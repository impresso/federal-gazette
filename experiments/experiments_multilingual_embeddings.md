# Multilingual Embeddings
This is an evaluation with the supervised [MUSE library](https://github.com/facebookresearch/MUSE) to pick the best multilingual alignments trained with Multivec and FastText.

Multivec trains on a parallel corpus, FastText embedding can be trained on a monolingual corpus and be aligned post hoc with MUSE.

We report the precision at 1 and  at 5 for kNN with cosine similarity and CSLS value. Even though the CSLS yields consistently better results than kNN, we don't consider this distance function as it is not supported by downstream applications and would need to be precomputed (also much slower than kNN). 

The evaluation is performed on the bilingual dictionary provided in MUSE (out-of-domain) and on a custom made dictionary (in-domain).

Please note the minimal count parameter that defines the vocabulary on which the evaluation is based. Due to potential out-of-vocabulary words, only results using an identical minimal count are meaningful. Moreover, the randomization of the corpus is not the same for all experiments, which may lead to slight differences. However, the results are consistent throughout the experiments.

## Non-standard hyperparameters
- FastText: -thread 20 -minCount 5 -ws 10 -dim 300 -minn 3 -maxn 6 -epoch 50
- MultiVec: --window-size 10 --sg

## Evaluation
### Out-of-Domain Evaluation DE -> FR
| Model                | Dim  | Train Params                      | Eval Params    | Aligning           | NN Precision @ 1 | NN Precision @ 5 | CSLS Precision @ 1 | CSLS Precision @ 5 |
| -------------------- | ---- | --------------------------------- | -------------- | ------------------ | ---------------- | ---------------- | ------------------ | ------------------ |
| FastText_v1          | 300  | no subword, iter 10, min-count 5  | max vocab 200k | MUSE               | 51.97            | 67.78            | 61.97              | 74.70              |
| FastText_v2          | 300  | subword 3-6, iter 50, min-count 5 | max vocab 200k | MUSE               | 54.06            | 68.65            | 61.58              | 74.38              |
| FastText_v2          | 300  | subword 3-6, iter 50, min-count 5 | max vocab 200k | RCSLS              | 56.36            | 71.73            | 62.94              | 74.47              |
| multivec_v4          | 300  | iter 20, min-count 10             | max vocab 200k | parallelism + MUSE | 68.22            | 78.29            | 73.02              | 83.88              |
| multivec_v4          | 300  | iter 20, min-count 10             | max vocab 200k | parallelism        | 69.30            | 78.76            | 73.49              | 84.81              |
| multivec_v5          | 300  | iter 50, min-count 10             | max vocab 200k | parallelism        | 69.66            | 78.33            | 73.37              | 84.52              |
| multivec_v6          | 300  | iter 50, min-count 5              | max vocab 200k | parallelism        | 65.07            | 78.21            | 71.64              | 85.08              |
| multivec_v6          | 300  | iter 50, min-count 5              | entire vocab   | parallelism        | 67.48            | 77.93            | 74.0               | 86.30              |
| multivec_v7          | 150  | iter 20, min-count 5              | max vocab 200k | parallelism        | 61.79            | 74.63            | 65.67              | 80.23              |
| ---                  | ---  | ---                               | ---            | ---                | ---              | ---              | ---                | ---                |
| multivec_new_corp_v1 | 100  | iter 20, min-count 5              | entire vocab   | parallelism        | 66.32            | 78.06            | 68.22              | 80.48              |
| multivec_new_corp_v1 | 150  | iter 20, min-count 5              | entire vocab   | parallelism        | **69.95**        | **82.21**        | 72.62              | 85.31              |
| multivec_new_corp_v1 | 300  | iter 20, min-count 5              | entire vocab   | parallelism        | 69.43            | 79.70            | 75.22              | 86.70              |

*new_corp refers to a new corpus. Thus, the results are not comparable to the older results due to different pre-processing.*

### In-Domain Evaluation DE -> FR

The bilingual in-domain dictionary was created by sampling from the Moses Translation file with the following command:

```bash
more mt_moses/train_de_fr/model/lex.e2f | awk  '{print $3" "$2" "$1}' | uniq  -f2 | egrep "0\.0{1,2}[1-9][0-9]+ [a-z]{7,15} [a-z]{7,15}" | sort -r | more | shuf -n 10000 | awk  '{print $3" "$2}' | egrep -v "-" > ../../dico-de-fr-sample.txt
```


To provide high-quality translations the sampled items where manually filtered and extended with some prominent translations. The final dataset consists of 191 pairs of words (DE-FR).


| Model                | Dim  | Train Params         | Eval Params  | Aligning    | NN Precision @ 1 | NN Precision @ 5 | CSLS Precision @ 1 | CSLS Precision @ 5 |
| -------------------- | ---- | -------------------- | ------------ | ----------- | ---------------- | ---------------- | ------------------ | ------------------ |
| multivec_v6          | 300  | iter 50, min-count 5 | entire vocab | parallelism | 43.02            | 59.88            | 39.53              | 56.98              |
| ---                  | ---  | ---                  | ---          | ---         | ---              | ---              | ---                | ---                |
| multivec_new_corp_v1 | 100  | iter 20, min-count 5 | entire vocab | parallelism | 38.06            | 58.06            | 36.12              | 52.90              |
| multivec_new_corp_v1 | 150  | iter 20, min-count 5 | entire vocab | parallelism | 42.58            | 65.16            | 41.29              | 65.80              |
| multivec_new_corp_v1 | 300  | iter 20, min-count 5 | entire vocab | parallelism | **49.03**        | 66.45**          | 47.10              | 68.39              |


### Provisional Conclusions

- FastText performs better in a monolingual setting
- FastText subword information seems to slightly improve performance quantitatively/qualitatively
- Aligning FastText with RCSLS (instead Procrustes) improves performance even when using classic kNN for the retrieval instead of CSLS
- MultiVec performs better than FastText in a bilingual setting
- additional Procrustes aligning with MUSE doesn't improve MultiVec alignments further
- an increase of epochs beyond 20 is unlikely to help
- the training of a parallel corpus may mitigate OCR issues 