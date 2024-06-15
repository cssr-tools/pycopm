%for j in range(len(dic['actnum_c'])):
%if dic['actnum_c'][j] == 1:
${dic["rock"][i][0]}${sum(dic['actnum_c'][0:j])} UNIFORM ${min_max[j][0]} ${min_max[j][1]}
%endif
%endfor
