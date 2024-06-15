SPECGRID
${dic['nx']} ${dic['ny']} ${dic['nz']} 1 F
/

COORD
% for i in range(len(dic['cr'])):
 ${f"{dic['cr'][i] : .3f}"}
% endfor
/

ZCORN
% for i in range(len(dic['zc'])):
 ${f"{dic['zc'][i] : .3f}"}
% endfor
/