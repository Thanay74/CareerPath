"""Generate clearly synthetic, reproducible career-family training profiles.

Labels are sampled first as latent career-family scenarios; profile scores are
then drawn from family-specific skill/interest/subject distributions. These rows
are development data, not empirical student outcomes.
"""
from pathlib import Path
import csv, random
SEED = 20260929
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "synthetic" / "career_training_profiles.csv"
LEVELS = ["10th", "12th", "Bachelor's", "Master's"]
FAMILIES = {
 "technology_engineering": {"technology":85,"innovation":72,"programming":78,"python":67,"data_analysis":65,"machine_learning":60,"cybersecurity":55,"web_development":55,"electronics":65,"mathematics":78,"computer_science":82,"physics":67,"logical_reasoning":78,"analytical_reasoning":78,"problem_solving":80,"research":58},
 "health_life_sciences": {"healthcare":88,"biology":85,"chemistry":77,"research":70,"research_methods":65,"attention_to_detail":78,"analytical_reasoning":72,"communication":66,"social_service":68},
 "business_finance": {"business":85,"entrepreneurship":73,"accountancy":80,"economics":79,"finance":77,"accounting":78,"sql":50,"data_analysis":60,"numerical_reasoning":78,"decision_making":75,"leadership":69},
 "creative_communication": {"creativity":86,"design":86,"communication":82,"english":82,"graphic_design":78,"ui_ux":74,"verbal_reasoning":80,"spatial_reasoning":75,"presentation":77,"history":62,"sociology":60},
 "public_social_research": {"social_service":83,"research":82,"political_science":78,"history":72,"sociology":77,"english":77,"research_methods":73,"verbal_reasoning":76,"critical_thinking":79,"communication":77,"professionalism":72}
}
STREAM_OPTIONS = {"technology_engineering":(["Science","Commerce","Arts/Humanities"],[.82,.13,.05]), "health_life_sciences":(["Science","Commerce","Arts/Humanities"],[.92,.04,.04]), "business_finance":(["Science","Commerce","Arts/Humanities"],[.17,.76,.07]), "creative_communication":(["Science","Commerce","Arts/Humanities"],[.08,.18,.74]), "public_social_research":(["Science","Commerce","Arts/Humanities"],[.13,.27,.60])}
FEATURES = sorted(set(k for d in FAMILIES.values() for k in d) | {"logical_reasoning","numerical_reasoning","verbal_reasoning","spatial_reasoning","analytical_reasoning","problem_solving","attention_to_detail","technology","research","creativity","entrepreneurship","leadership","healthcare","business","social_service","communication","design","innovation","programming","python","java","javascript","sql","data_analysis","machine_learning","web_development","cybersecurity","cloud_computing","accounting","finance","graphic_design","ui_ux","electronics","hardware","research_methods","teamwork","adaptability","time_management","critical_thinking","presentation","decision_making","professionalism","physics","chemistry","biology","mathematics","computer_science","english","accountancy","business_studies","economics","history","geography","political_science","sociology"})
def main(n_per_level=400):
    rng=random.Random(SEED); OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=["synthetic_id","education_level","stream",*FEATURES,"career_family"]); writer.writeheader()
        for level in LEVELS:
            for i in range(n_per_level):
                fam=rng.choice(list(FAMILIES)); archetype=FAMILIES[fam]; stream_options,stream_weights=STREAM_OPTIONS[fam]; stream=rng.choices(stream_options,weights=stream_weights,k=1)[0]; row={"synthetic_id":f"SYN-{level.replace(' ','').replace(chr(39),'')}-{i+1:04d}","education_level":level,"stream":stream}
                for feature in FEATURES:
                    mean=archetype.get(feature,48)
                    # Senior students show more accumulated specialization; irrelevant skills remain lower.
                    if feature in {"programming","python","java","javascript","sql","data_analysis","machine_learning","web_development","cybersecurity","cloud_computing","accounting","finance","graphic_design","ui_ux","electronics","hardware","research_methods"} and level in ("10th","12th"):
                        mean=min(mean, mean*.78 if feature not in archetype else mean*.86)
                    val=max(0,min(100,rng.gauss(mean,13)))
                    row[feature]=round(val,1)
                # Applicable subjects vary by stream and stage; missing values are intentional.
                for sub in ("physics","chemistry","biology","mathematics","computer_science","accountancy","business_studies","economics","english","history","geography","political_science","sociology"):
                    if sub not in ("english",) and stream=="Science" and sub in {"accountancy","business_studies","economics","history","geography","political_science","sociology"}: row[sub]=""
                    elif stream=="Commerce" and sub in {"physics","chemistry","biology","computer_science","history","geography","political_science","sociology"}: row[sub]=""
                    elif stream=="Arts/Humanities" and sub in {"physics","chemistry","biology","computer_science","accountancy","business_studies"}: row[sub]=""
                row["career_family"]=fam; writer.writerow(row)
    print(f"Wrote {n_per_level*len(LEVELS)} synthetic profiles to {OUT}")
if __name__=="__main__": main()
