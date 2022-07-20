# !conda activate jupyter_env
# !cd familial_analysis
# !python3
import tqdm
import json
import numpy as np
import pandas as pd
from statsmodels.discrete import conditional_models
from statsmodels.stats import multitest
from basic_tools import who_dict
from plot_tools import plot_odds_ratio, plot_crossed_odds_ratio, draw_grouped_bar_plot

OUTCOME = 'M13_RHEUMA'
data = pd.read_csv('data_'+OUTCOME+'.csv')
eps = json.load(open('eps_'+OUTCOME+'.json', 'r'))
eps_remove = ['E4_GRAVES_OPHT_STRICT', 'I9_RHEUFEV', 'L12_ALOPECAREATA', 'L12_DERMATHERP', 'L12_PEMPHIGOID', 'M13_MCTD']


def c_model(dataset, ep_index, who, ep_col_name):
    endpoint = eps[ep_index]
    n_cases = dataset[ep_col_name].sum()
    lr = conditional_models.ConditionalLogit(endog=dataset.outcome,
                                             exog=dataset[ep_col_name],
                                             groups=dataset.subclass).fit(disp=0)
    pval = lr.pvalues[0]
    se = lr.bse[0]
    hr_025 = np.exp(lr.conf_int().iloc[0, 0])
    hr_975 = np.exp(lr.conf_int().iloc[0, 1])
    subclass_list = []
    for i in range(data.subclass.max() + 1):  # 4 secs for a loop
        if len(data[data.subclass == i][ep_col_name].unique()) > 1:
            subclass_list.append(i)
    n_valid_pair00 = len(dataset[(dataset.subclass.isin(subclass_list)) &
                                 (dataset.outcome == 0) & (dataset[ep_col_name] == 0)])
    n_valid_pair01 = len(dataset[(dataset.subclass.isin(subclass_list)) &
                                 (dataset.outcome == 0) & (dataset[ep_col_name] == 1)])
    n_valid_pair10 = len(dataset[(dataset.subclass.isin(subclass_list)) &
                                 (dataset.outcome == 1) & (dataset[ep_col_name] == 0)])
    n_valid_pair11 = len(dataset[(dataset.subclass.isin(subclass_list)) &
                                 (dataset.outcome == 1) & (dataset[ep_col_name] == 1)])
    return [endpoint, who, se, pval, hr_025, hr_975, 1, len(subclass_list), n_cases,
            n_valid_pair00, n_valid_pair01, n_valid_pair10, n_valid_pair11]


def model_loop(dataset, note, res_df):
    for i in tqdm.tqdm(range(len(eps))):
        ep_col_mo = 'mo_ep' + str(i)
        ep_col_fa = 'fa_ep' + str(i)
        if ep_col_fa in dataset:
            res_fa = c_model(dataset, i, 'father')
            if res_fa:
                res_df = res_df.append(pd.Series(res_fa + [note], index=res_df.columns), ignore_index=True)
        if ep_col_fa in dataset:
            res_mo = c_model(dataset, i, 'mother')
            if res_mo:
                res_df = res_df.append(pd.Series(res_mo + [note], index=res_df.columns), ignore_index=True)
        if (ep_col_mo in dataset) & (ep_col_fa in dataset):
            dataset['exposure'] = dataset[ep_col_mo] | dataset[ep_col_fa]
            res_pa = c_model(dataset, i, 'parent')
            if res_pa:
                res_df = res_df.append(pd.Series(res_pa + [note], index=res_df.columns), ignore_index=True)
    dfr_sig, _ = multitest.fdrcorrection(res_df[res_df.note == note].pval)
    res_df.loc[res_df['dfr_sig'], 'dfr_sig'] = dfr_sig
    return res_df


res = pd.DataFrame(columns=["endpoint", "who", "se", "pval", "hr_025", "hr_975", 'dfr_sig', 'n_valid_group', "n_cases",
                            'n_valid_pair00', 'n_valid_pair01', 'n_valid_pair10', 'n_valid_pair11', "note"])
res = model_loop(data, 'all', res)
res = model_loop(data[data.sex == 1], 'women', res)
res = model_loop(data[data.sex == 0], 'men', res)
# summary statistics after removing those whose parents were born after 1961
data_sub = data[(data.fa_year_range < 1960) & (data.mo_year_range < 1960)]
res = model_loop(data_sub, 'all_sub', res)
res = model_loop(data_sub[data_sub.sex == 1], 'women_sub', res)
res = model_loop(data_sub[data_sub.sex == 0], 'men_sub', res)
# save the results
res.to_csv('res_'+OUTCOME+'.csv', index=None)

# plot the results
plot_odds_ratio(res[res.note == 'all'], eps, OUTCOME, bar_delta=.05)
plot_odds_ratio(res[res.note == 'women'], eps, OUTCOME, bar_delta=.05)
plot_odds_ratio(res[res.note == 'men'], eps, OUTCOME, bar_delta=.05)
plot_crossed_odds_ratio(res, ('women', 'men'), OUTCOME)

plot_odds_ratio(res[res.note == 'all_sub'], eps, OUTCOME, bar_cap=.05)
plot_crossed_odds_ratio(res, ('all', 'all_sub'), OUTCOME)

draw_grouped_bar_plot(res[res.note == 'all'], 'who', 'n_cases', title='All individuals')
draw_grouped_bar_plot(res[res.note == 'all_sub'], 'who', 'n_cases', title='Individuals whose parents were born < 1962')

