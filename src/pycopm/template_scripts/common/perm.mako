<%!
import numpy as np
%>\
{
%for j in range(len(active)):
%if active[j] == 1:
%if j == last_active_index:
"${rock_property_settings[i][0]}${np.sum(active[0:j])}": <${rock_property_settings[i][0]}${np.sum(active[0:j])}>
%else:
"${rock_property_settings[i][0]}${np.sum(active[0:j])}": <${rock_property_settings[i][0]}${np.sum(active[0:j])}>,
%endif
%endif
%endfor
}