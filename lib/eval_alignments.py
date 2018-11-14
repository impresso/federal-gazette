import glob
import pandas as pd
import xml.etree.ElementTree as ET
import re
import random

SAMPLE_SIZE = 10

# Get a sample of SAMPLE_SIZE for each alignment file


dfcols = ['year', 'id', 'src', 'trg', 'method', 'score',
          'script_head', 'scrip_tail', 'eval_head', 'eval_tail', 'comment']
df = pd.DataFrame(columns=dfcols)

for fname in glob.glob('*alignments.xml'):
    etree = ET.parse(fname)
    root = etree.getroot()

    n_elements = len(list(root.iter(tag='link')))

    try:
        samples = random.sample(range(0, n_elements), SAMPLE_SIZE)
    except ValueError:
        print('Sample size is large than number of alignments. {} will be skipped'.format(fname))
        continue

    for id, item in enumerate(root.iter(tag='link')):
        if id in samples:
            src, trg = item.get('xtargets').split(';')
            year = re.search(r'/(\d{4})/', src).group(1)
            method = item.get('method')
            score = item.get('score')
            script_head = "diff -W 200 -y <(head -n 30 " + \
                src + ") <(head -n 30 " + trg + ")"
            script_tail = "diff -W 200 -y <(tail -n 30 " + \
                src + ") <(tail -n 30 " + trg + ")"

            attr = [year, id, src, trg, method, score,
                    script_head, script_tail, '', '', '']

            df = df.append(pd.Series(attr, index=dfcols), ignore_index=True)

df = df.sort_values(by=['year']).reset_index(drop=True)

df.to_csv('eval_alignments.tsv', sep='\t')
