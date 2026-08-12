#!/usr/bin/env python

"""Script to write the LET saturation functions for Norne (with  hystereis)"""

import json

% for i in range(len(let_parameters)):
% if let_parameters[i][2] > 0 and execution_mode in ["files","ert"]:
with open("coeff_${str(let_parameters[i][0])}.json", 'r', encoding="utf8") as file:
    ${str(let_parameters[i][0])}C = json.load(file)
% endif
% endfor

# Properties
% for j in range(len(let_parameters)):
${str(let_parameters[j][0])} = [0.0 for _ in range(${number_tables})]
% endfor

% if let_parameters[j][2] > 0 and execution_mode in ["files","ert"]:
for i in range(${number_tables}):
% for j in range(len(let_parameters)):
    ${str(let_parameters[j][0])}[i] = ${str(let_parameters[j][0])}C[f"${str(let_parameters[j][0])}{i}"]
% endfor
% else:
% for i in range(number_tables):
% for j in range(len(let_parameters)):
${str(let_parameters[j][0])}[${i}] = ${float(let_parameters[j][1])}
% endfor
% endfor
% endif

with open("tables.inc", "w", encoding="utf8") as file:
    file.write("SWOFLET\n")
    for i in range(${number_tables}):
        file.write(f"0 0.0001 {max(1.1,lw[i])} {pow(10.0,ew[i])} {max(1.1,tw[i])} 0.5 0 0 {max(1.0,lmlto[i])*max(1.1,lo[i])} {pow(10.0,eo[i])} {max(1.1,to[i])} 1 0.69977 17.56167 0.95615 3.76138 0.03819 /\n")
    for i in range(${number_tables}):
        file.write(f"0 0.0001 {max(1.1,lw[i])} {pow(10.0,ew[i])} {max(1.1,tw[i])} 0.5 0 0 {max(1.1,lo[i])} {max(0.9,emlto[i])*pow(10.0,eo[i])} {max(1.0,tmlto[i])*max(1.1,to[i])} 1 0.69977 17.56167 0.95615 3.76138 0.03819 /\n")

    file.write("SGOFLET\n")
    for i in range(${number_tables}):
        file.write(f"0 0 {max(1.0,lmltg[i])*max(1.1,lg[i])} {pow(10.0,eg[i])} {max(1.1,tg[i])} 0.95 0 0.0001 {max(1.1,log[i])} {pow(10.0,eog[i])} {max(1.1,tog[i])} 0.99997432 1 1 1 0 0 / \n")

    for i in range(${number_tables}):
        file.write(f"0 0 {max(1.1,lg[i])} { max(1.0,emltg[i])*pow(10.0,eg[i])} {max(1.0,tmltg[i])*max(1.1,tg[i])} 0.95 0 0.0001 {max(1.1,log[i])} {pow(10.0,eog[i])} {max(1.1,tog[i])} 0.99997432 1 1 1 0 0 / \n")