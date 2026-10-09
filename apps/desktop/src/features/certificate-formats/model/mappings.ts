import type { MappingTargetDto, ValueMappingDto } from "@/lib/api";

export function emptyMapping(target: MappingTargetDto = "certificate_no"): ValueMappingDto {
  const unit: ValueMappingDto["unit"] = ["thickness_mm", "width_mm", "length_raw"].includes(target) ? "mm" :
    target === "weight_kg" ? "kg" : ["yield_strength_mpa", "tensile_strength_mpa"].includes(target) ? "MPa" :
      ["elongation_pct", "chemistry"].includes(target) ? "%" : null;
  return { target, unit, element: target === "chemistry" ? "C" : null,
    exponent: target === "chemistry" ? 0 : null, required: true, decimal_separator: "." };
}
