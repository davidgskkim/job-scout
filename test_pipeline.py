import json
from filters import tier1, tier2

def run_test():
    with open('jobs_test_data.json', 'r', encoding='utf-8') as f:
        jobs = json.load(f)
        
    print(f"Loaded {len(jobs)} jobs for testing.\n")
    
    for i, job in enumerate(jobs):
        print(f"--- Job {i+1}: {job['title']} ---")
        passed, reason, auto_pass = tier1.is_relevant(job)
        
        if not passed:
            print(f"[-] Tier 1 Rejected: {reason}\n")
            continue
            
        if auto_pass:
            print(f"[+] Auto-Passed (Tier 1): {reason}\n")
            continue
            
        print("[*] Tier 1 Passed, evaluating Tier 2...")
        decision, t2_reason = tier2.classify(job)
        if decision == "RELEVANT":
            print(f"[+] Tier 2 Passed: {t2_reason}")
        else:
            print(f"[-] Tier 2 Rejected: {t2_reason}")
        print()

if __name__ == "__main__":
    run_test()
