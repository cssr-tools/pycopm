files=(
    "test_outputs/docs_via_deck_dual_coarsening/dual_pressure-0pressure_i,1,k_t2.png"
    "test_outputs/docs_via_deck_drogon/drogon_pycopm_comparison.png"
    "test_outputs/docs_via_deck_drogon/drogon_generic_plopm.png"
    "test_outputs/docs_via_deck_drogon/sgas.gif"
    "test_outputs/docs_via_deck_norne/norne_plopm.png"
    "test_outputs/docs_config_views/index_plopm.png"
    "test_outputs/docs_via_deck_smeaheia/smeaheia.png"
    "test_outputs/docs_via_deck_spe10/spe10_plopm.png"
    "test_outputs/docs_via_deck_hello_world/hello_world_3_submodel_refined_rotated.png"
    "test_outputs/docs_via_deck_hello_world/hello_world_1_left.png"
    "test_outputs/docs_via_deck_hello_world/hello_world_3_submodel.png"
    "test_outputs/docs_via_deck_hello_world/hello_world_2.png"
    "test_outputs/docs_via_deck_hello_world/hello_world_1_right.png"
    "test_outputs/docs_via_deck_hello_world/hello_world_3_submodel_refined.png"
    "test_outputs/docs_via_config_drogon/drogon_coarser_plopm.png"
    "test_outputs/docs_theory_refinements/refinement_plopm.png"
    "test_outputs/docs_theory_coarsening/coarsening_plopm.png"
    "test_outputs/docs_theory_submodels/submodel_plopm.png"
    "test_outputs/docs_theory_submodels/submodel_porv_plopm.png"
    "test_outputs/docs_theory_submodels/submodelwell_plopm.png"
    "test_outputs/docs_theory_transformations/transformation_plopm.png"
)

missing_file="test_outputs/missing_docs_files.txt"
missing=0

rm -f "$missing_file"

for f in "${files[@]}"; do
    if [[ ! -f "$f" ]]; then
        echo "$f" >> "$missing_file"
        ((missing++))
    fi
done

if (( missing == 0 )); then
    echo "All figures and files exist."
else
    echo "$missing figure(s) or file(s) missing."
    echo "See $missing_file"
fi
