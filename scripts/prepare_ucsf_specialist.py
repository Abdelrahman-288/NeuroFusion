import argparse
from neurofusion.ucsf_loader import prepare_cache

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Prepare checked UCSF development cache')
    for name in ('root','partitions','output'):p.add_argument('--'+name,required=True)
    a=p.parse_args();prepare_cache(a.root,a.partitions,a.output)
