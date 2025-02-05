#!/usr/bin/env python

""""
Script to write the LET saturation functions
"""

import json

% for i in range(len(dic['LET'])):
% if dic['LET'][i][2] > 0 and dic['mode'] in ["files","ert"]:
with open("coeff_${str(dic['LET'][i][0])}.json", 'r', encoding="utf8") as file:
    ${str(dic['LET'][i][0])}C = json.load(file)
% endif
% endfor

# Properties
% for j in range(len(dic['LET'])):
${str(dic['LET'][j][0])} = [0.0 for i in range(${max(dic['satnum_c'])})]
% endfor

% for i in range(max(dic['satnum_c'])):
% for j in range(len(dic['LET'])):
% if dic['LET'][j][2] > 0 and dic['mode'] in ["files","ert"]:
${str(dic['LET'][j][0])}[${i}] = ${str(dic['LET'][j][0])}C["${str(dic['LET'][j][0])}${i}"]
% else:
${str(dic['LET'][j][0])}[${i}] = ${float(dic['LET'][j][1])}
% endif
% endfor
% endfor

with open("tables.inc", "w", encoding="utf8") as file:
    file.write("SWOFLET\n")
    for i in range(${max(dic['satnum_c'])}):
        file.write(f"0.00000  0.00010 {max(1.1,lw[i])} {pow(10.0,ew[i])} {max(1.1,tw[i])}  {kwow[i]}  0.00000  0.00000 { max(1.0,lmlto[i])*max(1.1,lo[i])} {pow(10.0,eo[i])} { max(1.1,to[i])}  {kwoo[i]}  0.69977 17.56167  0.95615  3.76138  0.03819 / \n")

    file.write("SGOFLET\n")
    for i in range(${max(dic['satnum_c'])}):
        file.write(f"  0.0  0.0 {max(1.0,lmltg[i])*max(1.1,lg[i])} {pow(10.0,eg[i])} {max(1.1,tg[i])}  {kwgw[i]}    0.0  0.0001 {max(1.1,log[i])} {pow(10.0,eog[i])} {max(1.1,tog[i])}  {kwgg[i]}    1.0  1.0  1.0  0.0   0.0 / \n")