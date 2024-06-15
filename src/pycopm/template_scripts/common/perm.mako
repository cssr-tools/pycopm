{
%for j in range(len(dic["actnum_c"])):
%if dic["actnum_c"][j] == 1:
%if j == last:
"${dic["rock"][i][0]}${sum(dic["actnum_c"][0:j])}": <${dic["rock"][i][0]}${sum(dic["actnum_c"][0:j])}>
%else:
"${dic["rock"][i][0]}${sum(dic["actnum_c"][0:j])}": <${dic["rock"][i][0]}${sum(dic["actnum_c"][0:j])}>,
%endif
%endif
%endfor
}