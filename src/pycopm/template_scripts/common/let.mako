% for j in range(dic["satnum_cmax"]-1):
"${dic["LET"][i][0]}${j}": <${dic["LET"][i][0]}${j}>,
% endfor
"${dic["LET"][i][0]}${dic["satnum_cmax"]-1}": <${dic["LET"][i][0]}${dic["satnum_cmax"]-1}>
}