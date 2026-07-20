// Mirrors shared/schemas/project.schema.json
// Hand-typed for v1; migrate to schema-generated types in phase 2.

export type MapType =
  | "surface_plan" | "surface_geological_plan" | "geological_plan"
  | "geological_section" | "progressive_mine_closure_plan"
  | "conceptual_plan" | "environment_plan" | "key_plan"
  | "financial_assurance_plan" | "year_wise_mining_plan" | "other";

export type UploadCategory =
  | "surface_plan" | "geological_plan" | "geological_section"
  | "environment_plan" | "key_plan" | "progressive_mine_closure_plan"
  | "conceptual_plan" | "financial_assurance_plan"
  | "borehole_data" | "chemical_analysis" | "production_data" 
  | "proposed_five_year_development_plan" | "year_1_plan" | "year_2_plan" 
  | "year_3_plan" | "year_4_plan" | "year_5_plan" 
  | "approved_mining_plan" | "annexures" | "other";

export type LayerType =
  | "lease_boundary" | "statutory_barrier_7_5m"
  | "boundary_60m" | "boundary_500m" | "grid_lines" | "contour"
  | "road" | "existing_tank" | "existing_infrastructure"
  | "existing_electric_line" | "existing_borehole" | "proposed_borehole"
  | "geological_zone" | "ultimate_pit_limit"
  | "year_pit" | "overburden_dump" | "topsoil_stack"
  | "backfill" | "plantation" | "mineral_stack_yard"
  | "haul_road" | "garland_drain" | "settling_tank"
  | "retaining_wall" | "fencing" | "office_shed"
  | "water_reservoir" | "village" | "sensitive_structure";

export type Alternative =
  | "base" | "conservative" | "aggressive"
  | "low_waste" | "environment_sensitive" | "cost_optimized"
  | "grade_blending" | "minimum_disturbance";

export interface ProjectDetails {
  project_name: string;
  applicant_name?: string;
  mineral?: string;
  village?: string;
  tehsil?: string;
  district?: string;
  state?: string;
  area_ha: number;
  map_type?: MapType;
  scale: string;
  survey_date?: string;
  plan_period_years: number;
}

export interface UploadedFile {
  id: string;
  filename: string;
  original_filename?: string;
  stored_path?: string;
  storage_backend?: string;
  category: UploadCategory;
  mime_type?: string;
  size_bytes?: number;
  pages?: number;
  selected_page?: number;
  uploaded_at?: string;
}

export interface LayerFeature {
  type: "Feature";
  geometry: GeoJSON.Geometry;
  properties: {
    layer_type: LayerType;
    year?: number;
    alternative?: Alternative;
    label?: string;
    color?: string;
    locked?: boolean;
  };
}

export interface FeatureCollection {
  type: "FeatureCollection";
  features: LayerFeature[];
}

export interface EngineeringInputs {
  production?: {
    annual_production_target_tonnes?: number;
    approved_capacity_tonnes_per_year?: number;
    working_days_per_year?: number;
    shifts_per_day?: number;
    hours_per_shift?: number;
  };
  bench?: {
    bench_height_m?: number;
    bench_width_m?: number;
    face_slope_degree?: number;
    overall_pit_slope_degree?: number;
    ultimate_pit_depth_m?: number;
  };
  mineral_waste?: {
    bulk_density_t_per_m3?: number;
    topsoil_thickness_m?: number;
    overburden_thickness_m?: number;
    mineral_recovery_percent?: number;
    reject_percent?: number;
  };
  machinery?: {
    excavator_bucket_capacity_m3?: number;
    number_of_excavators?: number;
    dumper_capacity_tonnes?: number;
    number_of_dumpers?: number;
    crusher_capacity_tph?: number;
    drill_machine_available?: boolean;
    blasting_required?: boolean;
  };
  grade?: Record<string, number>;
  environmental_constraints?: {
    water_body_distance_m?: number;
    village_distance_m?: number;
    sensitive_structure_distance_m?: number;
    electric_line_present?: boolean;
    drainage_present?: boolean;
    forest_land_present?: boolean;
    private_land_present?: boolean;
    government_land_present?: boolean;
  };
  assumed_fields?: string[];
}

export interface QuantityRow {
  year: number;
  pit_area_m2?: number;
  excavation_volume_m3?: number;
  mineral_volume_m3?: number;
  mineral_tonnes?: number;
  saleable_tonnes?: number;
  topsoil_m3?: number;
  overburden_m3?: number;
  backfill_m3?: number;
  plantation_area_m2?: number;
  stripping_ratio?: number;
}

export interface ValidationWarning {
  severity: "info" | "warning" | "error";
  code: string;
  message: string;
  feature_id?: string;
  alternative?: Alternative;
}

export interface MiningPlanProject {
  project_details: ProjectDetails;
  uploaded_files?: UploadedFile[];
  digitized_layers?: FeatureCollection;
  engineering_inputs?: EngineeringInputs;
  selected_alternatives?: Alternative[];
  generated_plans?: { alternative: Alternative; generated_at?: string; features: FeatureCollection }[];
  quantity_tables?: { alternative: Alternative; rows: QuantityRow[] }[];
  validation_warnings?: ValidationWarning[];
  created_at?: string;
  updated_at?: string;
}

export interface ProjectListItem {
  slug: string;
  project_name: string;
  updated_at?: string;
}

export type StepNumber = 1 | 2;

export interface StepDef {
  num: StepNumber;
  label: string;
  short: string;
  /** Steps on the happy path 1→2. */
  advanced?: boolean;
}

export const STEPS: StepDef[] = [
  { num: 1, label: "Project Setup",      short: "Project" },
  { num: 2, label: "Upload Plans",       short: "Upload" },
];
