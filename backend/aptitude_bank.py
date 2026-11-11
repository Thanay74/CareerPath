"""Project-level aptitude exercise question bank. Answers stay server-side."""

DOMAINS = ["logical_reasoning", "numerical_reasoning", "verbal_reasoning", "spatial_reasoning", "analytical_reasoning", "problem_solving", "attention_to_detail"]
LEVELS = ["10th", "12th", "Bachelor's", "Master's"]

_RAW = [
 ("logical_reasoning","If all roses are flowers and some flowers fade quickly, which statement must be true?",["All roses fade quickly","Some roses fade quickly","All roses are flowers","No flowers are roses"],2,"The first premise directly states that every rose belongs to the set of flowers."),
 ("logical_reasoning","Find the next letter: A, C, F, J, O, ?",["S","T","U","V"],2,"The jumps increase by one: +2, +3, +4, +5, then +6."),
 ("logical_reasoning","A is taller than B. C is shorter than B. Who is tallest?",["A","B","C","Cannot determine"],0,"A is taller than B, and B is taller than C."),
 ("logical_reasoning","If the code for CAT shifts each letter forward by one, what is the code for DOG?",["EPH","CNG","FQI","EOG"],0,"Each letter moves one position forward: D→E, O→P and G→H."),
 ("numerical_reasoning","What is 15% of 240?",["24","30","36","40"],2,"10% is 24 and 5% is 12, so 15% is 36."),
 ("numerical_reasoning","A bus travels 150 km in 3 hours at a constant speed. What is its speed?",["45 km/h","50 km/h","55 km/h","60 km/h"],1,"Speed equals distance divided by time: 150 ÷ 3 = 50."),
 ("numerical_reasoning","What is the next number: 3, 6, 12, 24, ?",["36","42","48","54"],2,"Each term is doubled."),
 ("numerical_reasoning","A price of 800 is reduced by 25%. What is the new price?",["550","580","600","625"],2,"A quarter of 800 is 200; 800 − 200 = 600."),
 ("verbal_reasoning","Choose the closest meaning of ‘concise’. ",["Brief","Unclear","Emotional","Detailed"],0,"Concise means expressing something briefly and clearly."),
 ("verbal_reasoning","Complete the analogy: Seed is to plant as egg is to …",["Nest","Bird","Feather","Shell"],1,"A seed can grow into a plant; an egg can develop into a bird."),
 ("verbal_reasoning","Choose the grammatically correct sentence.",["They was ready to begin.","They were ready to begin.","They is ready to begin.","They be ready to begin."],1,"The plural subject ‘they’ takes ‘were’ in the past tense."),
 ("spatial_reasoning","A square is rotated 90 degrees. What happens to its area?",["It doubles","It halves","It stays the same","It becomes zero"],2,"Rotation changes orientation, not the square's dimensions or area."),
 ("spatial_reasoning","A cube has all six faces painted and is cut into 27 equal smaller cubes. How many small cubes have paint on exactly three faces?",["4","6","8","12"],2,"Only the eight corner cubes have three painted faces."),
 ("spatial_reasoning","On a standard north-up map, you face east and turn left. Which direction do you face?",["North","South","East","West"],0,"A left turn from east points north."),
 ("spatial_reasoning","A paper is folded in half once and one hole is made away from the fold. How many holes appear when unfolded?",["1","2","3","4"],1,"The hole is mirrored across the single fold, producing two holes."),
 ("analytical_reasoning","Scores are 70, 80 and 90 with equal weighting. What is the mean?",["75","80","82","85"],1,"(70 + 80 + 90) ÷ 3 = 80."),
 ("analytical_reasoning","A survey has 40 responses; 10 chose option A. What fraction chose A?",["1/2","1/3","1/4","1/5"],2,"10 out of 40 simplifies to 1/4."),
 ("analytical_reasoning","Every shortlisted applicant meets the minimum requirement. Riya is shortlisted. What follows?",["Riya meets the minimum requirement","Riya is the top applicant","Riya is hired","Riya has the most experience"],0,"Shortlisted applicants are stated to meet the minimum, so this applies to Riya."),
 ("analytical_reasoning","A class has 12 students in Group A and 8 in Group B. What percentage are in Group B?",["20%","30%","40%","60%"],2,"Group B is 8 of 20 students: 8 ÷ 20 = 40%."),
 ("problem_solving","A device does not turn on. What is the best first step?",["Replace every component","Check the power connection","Discard the device","Install unrelated software"],1,"Start with a simple, likely cause that is easy to verify."),
 ("problem_solving","You have 30 minutes and three tasks. What is the most useful first action?",["Start the easiest without checking","Estimate importance and time for each","Do all at once","Wait until a deadline"],1,"Planning by importance and effort helps choose a sensible order."),
 ("problem_solving","Two routes reach the same destination. One is shorter but closed. What should you do?",["Use the closed route","Choose an available route","Stop travelling","Ignore the closure"],1,"A route must be available to be a workable solution."),
 ("attention_to_detail","Which code exactly matches AB-1847-XQ?",["AB-1847-XQ","AB-1874-XQ","AB-1847-QX","AB1847-XQ"],0,"Only the first option matches every character and separator."),
 ("attention_to_detail","Which pair is identical?",["careerpath / careerpath","assessment / assesment","specialization / specialisation","recommendation / recomendation"],0,"The first pair has the same spelling in both entries."),
 ("attention_to_detail","A form requires a date in YYYY-MM-DD. Which entry follows the format?",["10/11/2026","2026-11-10","11-10-2026","2026/11/10"],1,"The format uses a four-digit year, hyphen, two-digit month, hyphen, two-digit day."),
]

QUESTIONS = [{"question_id":f"APT{i:03d}","domain":d,"difficulty":"Foundational" if i < 9 else "Standard","education_levels":LEVELS,"question_text":q,"options":[{"id":chr(65+j),"text":o} for j,o in enumerate(opts)],"correct_option":chr(65+correct),"explanation":ex} for i,(d,q,opts,correct,ex) in enumerate(_RAW,1)]

def public_question(question):
    return {key:value for key,value in question.items() if key not in ("correct_option", "explanation")}
