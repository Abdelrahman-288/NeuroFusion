"""Decision aggregation for the predeclared three-seed UCSF comparison."""
from neurofusion.ucsf_sampling import compare_runs


def confirm_pairs(pairs, expected_seeds=(42,43,44)):
    if set(pairs)!=set(expected_seeds):raise ValueError('Complete predefined seed set required')
    results={str(seed):compare_runs(*pairs[seed]) for seed in expected_seeds}
    for row in results.values():
        row['decision']='seed passes predefined checks' if row['all_passed'] else 'seed fails predefined checks'
    passed=all(row['all_passed'] for row in results.values())
    return {'seeds':results,'all_seeds_passed':passed,
            'decision':'repeatable development improvement; independent evaluation still required' if passed else 'confirmation failed; retain baseline',
            'model_promoted':False,'independent_evaluation':False}
