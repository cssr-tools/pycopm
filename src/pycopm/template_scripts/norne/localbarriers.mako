-- This reservoir simulation deck is made available under the Open Database
-- License: http://opendatacommons.org/licenses/odbl/1.0/. Any rights in
-- individual contents of the database are licensed under the Database Contents
-- License: http://opendatacommons.org/licenses/dbcl/1.0/
  
-- Copyright (C) 2015 Statoil

-- Layer 8
EQUALS
--  'MULTZ'  0.005    ${original_to_output_i[6]} ${original_to_output_i[18]}  ${original_to_output_j[1]}  ${original_to_output_j[30]}  ${original_to_output_k[8]}  ${original_to_output_k[8]} /
'MULTZ'  0.02    ${original_to_output_i[6]} ${original_to_output_i[13]} ${original_to_output_j[30]}  ${original_to_output_j[50]} ${original_to_output_k[8]}  ${original_to_output_k[8]} /
/

-- MZ layer 10
EQUALS
  'MULTZ'   0.005  ${original_to_output_i[6]} ${original_to_output_i[14]}  ${original_to_output_j[11]}  ${original_to_output_j[18]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  C-3H
  'MULTZ'   0.03  ${original_to_output_i[14]} ${original_to_output_i[29]}  ${original_to_output_j[11]}  ${original_to_output_j[25]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  C south east
  'MULTZ'   0.05  ${original_to_output_i[14]} ${original_to_output_i[25]}  ${original_to_output_j[26]}  ${original_to_output_j[30]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  C-segm mid/B-2H
  'MULTZ'   0.25   ${original_to_output_i[6]} ${original_to_output_i[29]}  ${original_to_output_j[11]}  ${original_to_output_j[37]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  C-segm middle
  'MULTZ'   0.5   ${original_to_output_i[17]} ${original_to_output_i[17]}  ${original_to_output_j[42]}  ${original_to_output_j[54]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  C north west
  'MULTZ'   0.5    ${original_to_output_i[6]} ${original_to_output_i[12]}  ${original_to_output_j[38]}  ${original_to_output_j[39]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  C north west
  'MULTZ'   0.5    ${original_to_output_i[8]} ${original_to_output_i[12]}  ${original_to_output_j[40]}  ${original_to_output_j[40]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  C north west
  'MULTZ'   0.5   ${original_to_output_i[10]} ${original_to_output_i[12]}  ${original_to_output_j[41]}  ${original_to_output_j[43]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  C north west   
  'MULTZ'   0.5   ${original_to_output_i[18]} ${original_to_output_i[33]}  ${original_to_output_j[38]}  ${original_to_output_j[54]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  C1, D4 & D3
  'MULTZ'   0.5    ${original_to_output_i[6]} ${original_to_output_i[13]}  ${original_to_output_j[44]}  ${original_to_output_j[52]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  B-4AH
  'MULTZ'   0.01  ${original_to_output_i[13]} ${original_to_output_i[13]}  ${original_to_output_j[48]}  ${original_to_output_j[59]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  D-segm mid (B-4BH)
  'MULTZ'   0.01  ${original_to_output_i[14]} ${original_to_output_i[14]}  ${original_to_output_j[49]}  ${original_to_output_j[59]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  D-segm mid (B-4BH)
  'MULTZ'   0.01  ${original_to_output_i[15]} ${original_to_output_i[16]}  ${original_to_output_j[51]}  ${original_to_output_j[59]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  D-segm mid (B-4BH)
  'MULTZ'   0.05  ${original_to_output_i[17]} ${original_to_output_i[19]}  ${original_to_output_j[55]}  ${original_to_output_j[99]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  E1
  'MULTZ'   0.05  ${original_to_output_i[14]} ${original_to_output_i[14]}  ${original_to_output_j[60]}  ${original_to_output_j[62]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  E1
  'MULTZ'   0.05  ${original_to_output_i[15]} ${original_to_output_i[15]}  ${original_to_output_j[60]}  ${original_to_output_j[65]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  E1
  'MULTZ'   0.05  ${original_to_output_i[16]} ${original_to_output_i[16]}  ${original_to_output_j[60]}  ${original_to_output_j[69]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  E1 
  'MULTZ'   0.005  ${original_to_output_i[6]} ${original_to_output_i[9]}  ${original_to_output_j[52]}  ${original_to_output_j[60]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  F-3H/E-2H
  'MULTZ'   0.005  ${original_to_output_i[9]} ${original_to_output_i[9]}  ${original_to_output_j[53]}  ${original_to_output_j[57]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  F-3H/E-2H
  'MULTZ'   0.005 ${original_to_output_i[10]} ${original_to_output_i[10]}  ${original_to_output_j[54]}  ${original_to_output_j[58]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  F-3H/E-2H
  'MULTZ'   0.005 ${original_to_output_i[11]} ${original_to_output_i[11]}  ${original_to_output_j[55]}  ${original_to_output_j[58]}  ${original_to_output_k[10]}  ${original_to_output_k[10]}  /  F-3H/E-2H
/

-- MZ layer 15
EQUALS
  'MULTZ'   0.00003     ${original_to_output_i[6]} ${original_to_output_i[29]} ${original_to_output_j[11]} ${original_to_output_j[21]} ${original_to_output_k[15]} ${original_to_output_k[15]} / C south
  'MULTZ'   0.00005   ${original_to_output_i[6]} ${original_to_output_i[29]}  ${original_to_output_j[22]} ${original_to_output_j[39]}  ${original_to_output_k[15]}  ${original_to_output_k[15]} /  C middle
  'MULTZ'   0.000001 ${original_to_output_i[19]} ${original_to_output_i[29]}  ${original_to_output_j[39]} ${original_to_output_j[49]}  ${original_to_output_k[15]}  ${original_to_output_k[15]} /  C-1H
  'MULTZ'   1.0      ${original_to_output_i[19]} ${original_to_output_i[29]}  ${original_to_output_j[38]} ${original_to_output_j[45]}  ${original_to_output_k[17]}  ${original_to_output_k[17]} /  C-1H
  'MULTZ'   0.005    ${original_to_output_i[16]} ${original_to_output_i[19]}  ${original_to_output_j[48]} ${original_to_output_j[61]}  ${original_to_output_k[15]}  ${original_to_output_k[15]} /  E-1H/D-3H
  'MULTZ'   0.0008    ${original_to_output_i[8]} ${original_to_output_i[18]}  ${original_to_output_j[40]} ${original_to_output_j[40]}  ${original_to_output_k[15]}  ${original_to_output_k[15]} /  C north
  'MULTZ'   0.0008    ${original_to_output_i[9]} ${original_to_output_i[18]}  ${original_to_output_j[41]} ${original_to_output_j[41]}  ${original_to_output_k[15]}  ${original_to_output_k[15]} /
  'MULTZ'   0.0008   ${original_to_output_i[10]} ${original_to_output_i[18]}  ${original_to_output_j[42]} ${original_to_output_j[43]}  ${original_to_output_k[15]}  ${original_to_output_k[15]} /
  'MULTZ'   0.0008   ${original_to_output_i[11]} ${original_to_output_i[18]}  ${original_to_output_j[44]} ${original_to_output_j[44]}  ${original_to_output_k[15]}  ${original_to_output_k[15]} /
  'MULTZ'   0.0008   ${original_to_output_i[12]} ${original_to_output_i[18]}  ${original_to_output_j[45]} ${original_to_output_j[45]}  ${original_to_output_k[15]}  ${original_to_output_k[15]} /
  'MULTZ'   0.0008   ${original_to_output_i[13]} ${original_to_output_i[18]}  ${original_to_output_j[46]} ${original_to_output_j[47]}  ${original_to_output_k[15]}  ${original_to_output_k[15]} /
  'MULTZ'   0.0008   ${original_to_output_i[14]} ${original_to_output_i[15]}  ${original_to_output_j[48]} ${original_to_output_j[48]}  ${original_to_output_k[15]}  ${original_to_output_k[15]} /
  'MULTZ'   0.0008   ${original_to_output_i[15]} ${original_to_output_i[15]}  ${original_to_output_j[49]} ${original_to_output_j[50]}  ${original_to_output_k[15]}  ${original_to_output_k[15]} /
  
  'MULTZ'   0.01      ${original_to_output_i[12]} ${original_to_output_i[12]} ${original_to_output_j[46]} ${original_to_output_j[56]} ${original_to_output_k[15]} ${original_to_output_k[15]} / D-segm
  'MULTZ'   0.01      ${original_to_output_i[13]} ${original_to_output_i[13]} ${original_to_output_j[48]} ${original_to_output_j[59]} ${original_to_output_k[15]} ${original_to_output_k[15]} / D-segm
  'MULTZ'   0.01      ${original_to_output_i[14]} ${original_to_output_i[14]} ${original_to_output_j[49]} ${original_to_output_j[62]} ${original_to_output_k[15]} ${original_to_output_k[15]} / D-segm
  'MULTZ'   0.01      ${original_to_output_i[15]} ${original_to_output_i[15]} ${original_to_output_j[51]} ${original_to_output_j[65]} ${original_to_output_k[15]} ${original_to_output_k[15]} / D-segm
  'MULTZ'   0.01      ${original_to_output_i[16]} ${original_to_output_i[19]} ${original_to_output_j[62]} ${original_to_output_j[69]} ${original_to_output_k[15]} ${original_to_output_k[15]} / D-segm
  'MULTZ'   0.01      ${original_to_output_i[17]} ${original_to_output_i[19]} ${original_to_output_j[70]} ${original_to_output_j[99]} ${original_to_output_k[15]} ${original_to_output_k[15]} / D-segm
   MULTZ    0.0035      ${original_to_output_i[6]}  ${original_to_output_i[7]} ${original_to_output_j[40]} ${original_to_output_j[60]} ${original_to_output_k[15]} ${original_to_output_k[15]} / D, E west
   MULTZ    0.0035      ${original_to_output_i[8]}  ${original_to_output_i[8]} ${original_to_output_j[41]} ${original_to_output_j[60]} ${original_to_output_k[15]} ${original_to_output_k[15]} /
   MULTZ    0.0035      ${original_to_output_i[9]}  ${original_to_output_i[9]} ${original_to_output_j[42]} ${original_to_output_j[52]} ${original_to_output_k[15]} ${original_to_output_k[15]} /
   MULTZ    0.0035     ${original_to_output_i[10]}  ${original_to_output_i[10]} ${original_to_output_j[44]} ${original_to_output_j[49]} ${original_to_output_k[15]} ${original_to_output_k[15]} /
/

-- D-1H water
EQUALS
  'MULTZ'    1.0  ${original_to_output_i[22]}  ${original_to_output_i[24]}  ${original_to_output_j[21]}  ${original_to_output_j[22]}  ${original_to_output_k[11]}  ${original_to_output_k[11]} /  
  'MULTZ'    0.1  ${original_to_output_i[21]}  ${original_to_output_i[25]}  ${original_to_output_j[17]}  ${original_to_output_j[19]}  ${original_to_output_k[15]}  ${original_to_output_k[15]} /    
  'MULTZ'    1.0  ${original_to_output_i[22]}  ${original_to_output_i[24]}  ${original_to_output_j[17]}  ${original_to_output_j[19]}  ${original_to_output_k[17]}  ${original_to_output_k[17]} / 
  'MULTZ'    1.0  ${original_to_output_i[22]}  ${original_to_output_i[24]}  ${original_to_output_j[15]}  ${original_to_output_j[17]}  ${original_to_output_k[18]}  ${original_to_output_k[18]} /   
/  

-- B-1 & B-3 water
EQUALS
  'MULTZ'    0.1 ${original_to_output_i[12]}  ${original_to_output_i[13]}  ${original_to_output_j[34]}  ${original_to_output_j[35]}  ${original_to_output_k[15]}  ${original_to_output_k[15]} /  
/ 

-- RFT D_-H
EQUALS
  'MULTZ'  0.1     ${original_to_output_i[16]} ${original_to_output_i[19]} ${original_to_output_j[47]} ${original_to_output_j[53]} ${original_to_output_k[18]} ${original_to_output_k[18]} /  D-3H
/
