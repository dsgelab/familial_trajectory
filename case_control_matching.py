import pandas as pd
import tqdm
import itertools

# define matching ratio
MATCH_NUM = 3

# load data
df = pd.read_csv('df.csv')

# split into case and potential control
cases = df[~df.age_onset.isna()] # 15102
control_for_match = df[df.age_onset.isna()]

# get a list of possible strata
df_for_match = cases[['ID', 'sex', 'ch_year_range', 'fa_year_range', 'mo_year_range', 'sib_number']]
match_var = [df[col].unique().tolist() for col in df_for_match.columns[1:]]
match_permutation = list(itertools.product(*match_var)) # 3296000 -> 10560 -> 1734

# keep only existed strata
match_permutation_keep = []
for i in tqdm.tqdm(match_permutation):
    sex, ch_year, fa_year, mo_year, sib_num = i
    try:
        match = cases[(cases.sex == sex) &
                      (cases.ch_year_range == ch_year) &
                      (cases.fa_year_range == fa_year) &
                      (cases.mo_year_range == mo_year) &
                      (cases.sib_number == sib_num)]
        if len(match) != 0:
            match_permutation_keep.append({'conditions': i, 'n_cases': len(match)})

    except Exception as e:
        print(e, i)

# find failed strata to remove
match_failed = []
control_ids = []
for i in tqdm.tqdm(match_permutation_keep):
    sex, ch_year, fa_year, mo_year, sib_num = i['conditions']
    try:
        potential_control = control_for_match[(control_for_match.sex == sex)&
                                              (control_for_match.ch_year_range == ch_year)&
                                              (control_for_match.fa_year_range == fa_year)&
                                              (control_for_match.mo_year_range == mo_year)&
                                              (control_for_match.sib_number == sib_num)]
        if len(potential_control) < MATCH_NUM*i['n_cases']:
            match_failed.append(i)
        else:
            potential_control = potential_control.sample(n=MATCH_NUM*i['n_cases'])
            control_ids += potential_control.ID.tolist()
    except:
        match_failed.append(i)

# remove all the cases that cannot find enough matched controls
cases_to_remove = []
for i in tqdm.tqdm(match_failed):
    sex, ch_year, fa_year, mo_year, sib_num = i['conditions']
    try:
        potential_not_cases = cases[(cases.sex == sex) &
                                    (cases.ch_year_range == ch_year) &
                                    (cases.fa_year_range == fa_year) &
                                    (cases.mo_year_range == mo_year) &
                                    (cases.sib_number == sib_num)]
        for j in potential_not_cases.ID:
            cases_to_remove.append(j)
    except:
        print(i)
cases = cases[~cases.ID.isin(cases_to_remove)]
control = control_for_match[control_for_match.ID.isin(control_ids)]

# merge the data and save
data = pd.concat([cases, control], axis=0, ignore_index=True)
data = data.sample(frac=1)
data.to_csv('data.csv', index=None)