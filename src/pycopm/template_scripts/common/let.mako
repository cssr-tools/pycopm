{
% for j in range(max(dic["satnum_c"])-1):
"${dic["LET"][i][0]}${j}": <${dic["LET"][i][0]}${j}>,
% endfor
"${dic["LET"][i][0]}${max(dic["satnum_c"])-1}": <${dic["LET"][i][0]}${max(dic["satnum_c"])-1}>
}