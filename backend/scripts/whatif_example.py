"""Run 64 paired synthetic scenarios without a database or TMDB key."""
import argparse,json
from app.repository import canonical_hash
from app.whatif.example import example_inputs
from app.whatif.engine import compare

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--control',action='store_true',help='Keep the original director; every paired change must be zero.');args=parser.parse_args()
    inputs=example_inputs(control=args.control);result=compare(inputs)
    print(json.dumps(dict(synthetic=True,note='Invented exercise; no saved film is changed.',input_hash=canonical_hash(inputs.model_dump(mode='json')),output_hash=canonical_hash(result),comparison=result),indent=2))
if __name__=='__main__':main()
