{
% for j in range(number_tables-1):
"${let_parameters[i][0]}${j}": <${let_parameters[i][0]}${j}>,
% endfor
"${let_parameters[i][0]}${number_tables-1}": <${let_parameters[i][0]}${number_tables-1}>
}