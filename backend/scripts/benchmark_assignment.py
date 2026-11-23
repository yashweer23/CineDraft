"""Compare Phase 12 reference and current exact solver on identical inputs."""
import argparse, cProfile, hashlib, json, pstats, statistics, time
from pathlib import Path
from app.domain import Role, Slot
from app.repository import canonical_hash
from app.drafting import assignment as current
from app.validation import assignment_phase12 as reference
from app.validation.metrics import machine

def workloads():
    for people, remaining in [(30,8),(100,8),(1000,8),(100,4)]:
        pool=[current.Talent(f'p{i:04}',r.value,((i*17+len(r))%47+1)*25000)
              for i in range(people) for r in Role if (i+len(r))%3!=0]
        yield f'{people}-people-{remaining}-slots',pool,list(Slot)[8-remaining:],{'p0000','p0001'}

def measure(fn, pool, slots, used, iterations):
    start=time.perf_counter()
    for _ in range(iterations): fn(pool,slots,used)
    return (time.perf_counter()-start)*1000/iterations

def profile(fn,pool,slots,used):
    p=cProfile.Profile();p.enable()
    for _ in range(20):fn(pool,slots,used)
    p.disable();stats=pstats.Stats(p)
    return [dict(function=f'{Path(key[0]).name}:{key[2]}',calls=value[1],self_seconds=value[2],cumulative_seconds=value[3])
            for key,value in sorted(stats.stats.items(),key=lambda item:-item[1][3])[:8]]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rounds',type=int,default=7);p.add_argument('--iterations',type=int,default=20)
    p.add_argument('--out',type=Path,default=Path('../validation-output/assignment.json'));args=p.parse_args()
    if not 3<=args.rounds<=101 or not 1<=args.iterations<=1000:p.error('Use 3..101 rounds and 1..1000 iterations')
    cases=[]
    for name,pool,slots,used in workloads():
        old=reference.minimum_assignment(pool,slots,used);new=current.minimum_assignment(pool,slots,used)
        if old!=new: raise AssertionError('Assignment cost or exact witness changed')
        samples={'phase12':[],'phase13':[]};functions={'phase12':reference.minimum_assignment,'phase13':current.minimum_assignment}
        for fn in functions.values():measure(fn,pool,slots,used,3)
        for index in range(args.rounds):
            for key in (['phase12','phase13'] if index%2==0 else ['phase13','phase12']):
                samples[key].append(measure(functions[key],pool,slots,used,args.iterations))
        medians={key:statistics.median(values) for key,values in samples.items()}
        cases.append(dict(name=name,person_roles=len(pool),remaining_slots=len(slots),exact_output_hash=canonical_hash(new),
            samples_ms=samples,median_ms=medians,speedup=medians['phase12']/medians['phase13']))
    _,pool,slots,used=list(workloads())[1]
    result=dict(schema_version='phase13-solver-benchmark-v1',machine=machine(),iterations_per_round=args.iterations,rounds=args.rounds,
        reference_sha256=hashlib.sha256(Path(reference.__file__).read_bytes()).hexdigest(),
        current_sha256=hashlib.sha256(Path(current.__file__).read_bytes()).hexdigest(),
        method='3 warmups per function/case; alternating measurement order; median milliseconds per solve. Exact output equality checked outside timing. Single process, no HTTP, database or speed threshold.',
        cases=cases,profile_phase12=profile(reference.minimum_assignment,pool,slots,used),profile_phase13=profile(current.minimum_assignment,pool,slots,used))
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([dict(name=c['name'],**c['median_ms'],speedup=c['speedup']) for c in cases],indent=2))
if __name__=='__main__':main()
