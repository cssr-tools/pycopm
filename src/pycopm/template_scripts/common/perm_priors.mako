<%!
import numpy as np
%>\
%for j in range(len(active)):
%if active[j] == 1:
${rock_property_settings[i][0]}${np.sum(active[0:j])} UNIFORM ${values_c_min_max[j][0]} ${values_c_min_max[j][1]}
%endif
%endfor
