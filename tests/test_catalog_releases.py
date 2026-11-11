import json
import multiprocessing
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services import catalog_releases as releases


def _process_publish(csv_path, metadata_path, releases_dir, active_path, marker_path, lock_path, rows, fingerprint, result_queue):
    from backend.services.catalog_releases import CatalogReleaseError, publish_catalog
    try:
        snapshot = publish_catalog(rows, fingerprint, csv_path, metadata_path, active_manifest=active_path, managed_marker=marker_path, releases_dir=releases_dir, activation_lock=lock_path)
        result_queue.put(("published", snapshot.release_id))
    except CatalogReleaseError as exc:
        result_queue.put(("rejected", str(exc)))


def _process_load(csv_path, metadata_path, releases_dir, active_path, marker_path, result_queue):
    from backend.services.catalog_releases import load_active_catalog
    snapshot=load_active_catalog(csv_path,metadata_path,active_manifest=active_path,managed_marker=marker_path,releases_dir=releases_dir)
    result_queue.put((snapshot.release_id,snapshot.rows[0]['description'],snapshot.fingerprint))


class CatalogReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        data=Path(__file__).resolve().parents[1]/'data'
        self.csv=self.root/'canonical.csv'; self.metadata=self.root/'canonical.json'
        shutil.copyfile(data/'career_knowledge_base.csv',self.csv)
        shutil.copyfile(data/'career_metadata.json',self.metadata)
        self.releases=self.root/'releases'; self.active=self.root/'active.json'; self.marker=self.root/'managed.json'; self.lock=self.root/'activation.lock'
        self.base=releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases)

    def tearDown(self): self.tmp.cleanup()

    def publish_rows(self, rows, expected=None):
        return releases.publish_catalog(rows,expected or self.base.fingerprint,self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases,activation_lock=self.lock)

    def changed_rows(self, description):
        rows=[dict(row) for row in self.base.rows]
        rows[0]['description']=description
        return rows

    def test_malformed_pointer_and_incomplete_release_are_rejected_without_fallback(self):
        self.active.write_text('{invalid',encoding='utf-8')
        with self.assertRaisesRegex(releases.CatalogReleaseError,'malformed JSON'):
            releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases)
        self.active.write_text(json.dumps({'schema_version':1,'release_id':'a'*64}),encoding='utf-8')
        with self.assertRaisesRegex(releases.CatalogReleaseError,'incomplete or missing'):
            releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases)

    def test_corrupt_release_files_are_rejected(self):
        active=self.publish_rows(self.changed_rows('Version one'))
        (self.releases/active.release_id/'career_metadata.json').write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(releases.CatalogReleaseError,'does not match'):
            releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases)

    def test_malformed_release_manifest_is_rejected(self):
        active=self.publish_rows(self.changed_rows('Version one'))
        (self.releases/active.release_id/'release.json').write_text('{bad',encoding='utf-8')
        with self.assertRaisesRegex(releases.CatalogReleaseError,'malformed JSON'):
            releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases)

    def test_deleted_active_manifest_is_rejected_after_release_mode_is_established(self):
        self.publish_rows(self.changed_rows('Version one'))
        self.active.unlink()
        with self.assertRaisesRegex(releases.CatalogReleaseError,'manifest is missing'):
            releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases)

    def test_stale_draft_is_rejected(self):
        first=self.publish_rows(self.changed_rows('Version one'))
        with self.assertRaisesRegex(releases.CatalogReleaseError,'changed since this draft'):
            self.publish_rows(self.changed_rows('Stale version'),expected=self.base.fingerprint)
        active=releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases)
        self.assertEqual(active.fingerprint,first.fingerprint)

    def test_failure_before_activation_preserves_previous_active_pointer(self):
        old=self.publish_rows(self.changed_rows('Version one'))
        pointer=self.active.read_bytes()
        with patch.object(releases,'_prepare_release',side_effect=OSError('injected before activation')):
            with self.assertRaises(releases.CatalogActivationError) as raised:
                self.publish_rows(self.changed_rows('Version two'),expected=old.fingerprint)
        self.assertEqual(raised.exception.outcome,'not_committed')
        self.assertEqual(self.active.read_bytes(),pointer)
        self.assertEqual(releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases).fingerprint,old.fingerprint)

    def test_failed_pointer_replace_keeps_old_active_release(self):
        old=self.publish_rows(self.changed_rows('Version one'))
        pointer=self.active.read_bytes()
        with patch.object(releases.os,'replace',side_effect=OSError('injected pointer replacement failure')):
            with self.assertRaises(releases.CatalogActivationError) as raised:
                self.publish_rows(self.changed_rows('Version two'),expected=old.fingerprint)
        self.assertEqual(raised.exception.outcome,'not_committed')
        self.assertEqual(self.active.read_bytes(),pointer)
        self.assertEqual(releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases).fingerprint,old.fingerprint)

    def test_directory_fsync_failure_after_pointer_replace_reports_committed(self):
        old=self.publish_rows(self.changed_rows('Version one'))
        real_fsync_directory=releases._fsync_directory
        def fail_after_pointer_replace(path):
            if Path(path)==self.active.parent:
                raise OSError('injected directory fsync failure')
            return real_fsync_directory(path)
        with patch.object(releases,'_fsync_directory',side_effect=fail_after_pointer_replace):
            with self.assertRaises(releases.CatalogActivationError) as raised:
                self.publish_rows(self.changed_rows('Version two'),expected=old.fingerprint)
        self.assertEqual(raised.exception.outcome,'committed')
        self.assertTrue(raised.exception.durability_uncertain)
        self.assertEqual(raised.exception.snapshot.rows[0]['description'],'Version two')
        self.assertEqual(releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases).release_id,raised.exception.release_id)

    def test_unreadable_final_active_state_is_reported_indeterminate(self):
        first=self.publish_rows(self.changed_rows('Version one'))
        real_load=releases.load_active_catalog
        calls=0
        def fail_verification(*args,**kwargs):
            nonlocal calls
            calls+=1
            if calls>1:
                raise releases.CatalogReleaseError('injected active-state read failure')
            return real_load(*args,**kwargs)
        real_fsync_directory=releases._fsync_directory
        def fail_after_pointer_replace(path):
            if Path(path)==self.active.parent:
                raise OSError('injected directory fsync failure')
            return real_fsync_directory(path)
        with patch.object(releases,'load_active_catalog',side_effect=fail_verification), patch.object(releases,'_fsync_directory',side_effect=fail_after_pointer_replace):
            with self.assertRaises(releases.CatalogActivationError) as raised:
                self.publish_rows(self.changed_rows('Version two'),expected=first.fingerprint)
        self.assertEqual(raised.exception.outcome,'indeterminate')
        self.assertIsNone(raised.exception.snapshot)

    def test_restart_reload_and_rollback_keep_known_good_releases(self):
        first=self.publish_rows(self.changed_rows('Version one'))
        second=self.publish_rows(self.changed_rows('Version two'),expected=first.fingerprint)
        restarted=releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases)
        self.assertEqual(restarted.release_id,second.release_id)
        self.assertEqual(restarted.rows[0]['description'],'Version two')
        rollback=releases.restore_release(first.release_id,second.fingerprint,self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases,activation_lock=self.lock)
        self.assertEqual(rollback.release_id,first.release_id)
        self.assertEqual(rollback.rows[0]['description'],'Version one')
        releases_list=releases.list_releases(active_manifest=self.active,releases_dir=self.releases,managed_marker=self.marker)
        self.assertEqual(sum(item['active'] for item in releases_list),1)
        self.assertGreaterEqual(len(releases_list),3) # includes the original canonical pair

    def test_recommendation_read_context_pins_csv_and_metadata_to_one_release(self):
        first=self.publish_rows(self.changed_rows('Version one'))
        with releases.catalog_read_context(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases) as pinned:
            second=releases.publish_catalog(self.changed_rows('Version two'),first.fingerprint,self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases,activation_lock=self.lock)
            still_pinned=releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases)
            self.assertEqual(still_pinned.release_id,first.release_id)
            self.assertEqual(pinned.release_id,first.release_id)
        after_context=releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases)
        self.assertEqual(after_context.release_id,second.release_id)

    def test_interrupted_after_atomic_pointer_switch_reloads_complete_new_release(self):
        old=self.publish_rows(self.changed_rows('Version one'))
        real_replace=releases._atomic_replace_manifest
        def replace_then_interrupt(pointer,release_id):
            real_replace(pointer,release_id)
            raise RuntimeError('simulated process interruption after atomic switch')
        with patch.object(releases,'_atomic_replace_manifest',side_effect=replace_then_interrupt):
            with self.assertRaises(releases.CatalogActivationError) as raised:
                self.publish_rows(self.changed_rows('Version two'),expected=old.fingerprint)
        self.assertEqual(raised.exception.outcome,'committed')
        restarted=releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases)
        self.assertEqual(restarted.rows[0]['description'],'Version two')
        self.assertEqual(restarted.fingerprint,releases._fingerprint(restarted.csv_bytes,restarted.metadata_bytes))
        ctx=multiprocessing.get_context('spawn'); queue=ctx.Queue()
        process=ctx.Process(target=_process_load,args=(str(self.csv),str(self.metadata),str(self.releases),str(self.active),str(self.marker),queue))
        process.start(); process.join(15)
        self.assertEqual(process.exitcode,0)
        release_id,description,fingerprint=queue.get(timeout=3)
        self.assertEqual((release_id,description,fingerprint),(restarted.release_id,'Version two',restarted.fingerprint))

    def test_concurrent_process_activation_allows_only_one_stale_base_writer(self):
        ctx=multiprocessing.get_context('spawn'); result_queue=ctx.Queue()
        workers=[ctx.Process(target=_process_publish,args=(str(self.csv),str(self.metadata),str(self.releases),str(self.active),str(self.marker),str(self.lock),self.changed_rows(f'Concurrent {i}'),self.base.fingerprint,result_queue)) for i in range(2)]
        for worker in workers: worker.start()
        for worker in workers:
            worker.join(15)
            self.assertEqual(worker.exitcode,0)
        results=[result_queue.get(timeout=3) for _ in workers]
        self.assertEqual([state for state,_ in results].count('published'),1)
        self.assertEqual([state for state,_ in results].count('rejected'),1)
        active=releases.load_active_catalog(self.csv,self.metadata,active_manifest=self.active,managed_marker=self.marker,releases_dir=self.releases)
        self.assertIn(active.rows[0]['description'],{'Concurrent 0','Concurrent 1'})


if __name__=='__main__': unittest.main()
