"""Download and preserve the official UCI Student Performance archive."""
from pathlib import Path
import urllib.request, zipfile, shutil, subprocess
ROOT=Path(__file__).resolve().parent; RAW=ROOT/'raw'; RAW.mkdir(exist_ok=True)
url='https://archive.ics.uci.edu/static/public/320/student+performance.zip'
archive=RAW/'student_performance.zip'
try:
    urllib.request.urlretrieve(url,archive)
except Exception:
    # Some managed Windows TLS providers fail certificate negotiation in urllib.
    node=shutil.which('node')
    if not node: raise
    script="fetch(process.argv[1]).then(async r=>{if(!r.ok)throw Error('HTTP '+r.status);require('fs').writeFileSync(process.argv[2],Buffer.from(await r.arrayBuffer()))}).catch(e=>{console.error(e);process.exit(1)})"
    subprocess.run([node,'-e',script,url,str(archive)],check=True)
destination=RAW/'student_performance'; destination.mkdir(exist_ok=True)
with zipfile.ZipFile(archive) as z: z.extractall(destination)
nested=destination/'student.zip'
if nested.exists():
    with zipfile.ZipFile(nested) as z: z.extractall(destination/'extracted')
print(f'Downloaded {archive}; official CSV files are in {destination/"extracted"}')
