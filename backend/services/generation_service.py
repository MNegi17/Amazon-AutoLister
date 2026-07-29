import os
import openpyxl
import logging
import re
from collections import defaultdict
from ..models import HardcodedDefault, LearnedMapping
from .excel_processor import ExcelProcessor
from .rule_engine import RuleEngine
from .validation_service import ValidationService
from .learning_engine import LearningEngine

logger = logging.getLogger(__name__)

def is_brand_attribute(attr_name: str) -> bool:
    name_lower = attr_name.lower()
    if "brand" not in name_lower:
        return False
    if name_lower.endswith(".value") or name_lower == "brand_name" or name_lower == "brand":
        if "relationship" not in name_lower and "group" not in name_lower:
            return True
    return False

def is_epi_entity_attribute(attr_name: str) -> bool:
    name_lower = attr_name.lower()
    return "external_product_information" in name_lower and name_lower.endswith(".entity")

def is_epi_value_attribute(attr_name: str) -> bool:
    name_lower = attr_name.lower()
    return "external_product_information" in name_lower and name_lower.endswith(".value")

def is_color_map_attribute(attr_name: str) -> bool:
    name_lower = attr_name.lower()
    if "color" not in name_lower:
        return False
    return "standardized_values" in name_lower or "color_map" in name_lower

def is_color_name_attribute(attr_name: str) -> bool:
    name_lower = attr_name.lower()
    if "color" not in name_lower:
        return False
    return name_lower.endswith(".value") and "standardized_values" not in name_lower and "color_map" not in name_lower

def is_department_attribute(attr_name: str) -> bool:
    name_lower = attr_name.lower()
    return "department" in name_lower

def is_target_gender_attribute(attr_name: str) -> bool:
    name_lower = attr_name.lower()
    return "target_gender" in name_lower or "target_audience" in name_lower

def is_size_value_attribute(attr_name: str) -> bool:
    name_lower = attr_name.lower()
    if any(x in name_lower for x in ["size_system", "size_class", "body_type", "width", "size_to", "to_size", "age_group"]):
        return False
    return ".size" in name_lower or "size_value" in name_lower or "size_name" in name_lower or name_lower.endswith(".size")

def is_size_range_attribute(attr_name: str) -> bool:
    name_lower = attr_name.lower()
    return ".size_to" in name_lower or ".to_size" in name_lower or "size_range" in name_lower or "size_to_range" in name_lower

def is_material_attribute(attr_name: str) -> bool:
    name_lower = attr_name.lower()
    return "material" in name_lower or "fabric" in name_lower

def is_baby_size(size_val: str) -> bool:
    if not size_val:
        return False
    s = str(size_val).upper().strip()
    if "MONTH" in s or "MON" in s:
        return True
    if re.search(r'\b\d+[-\s]?\d*\s*M\b', s) or re.search(r'^\d+M$', s):
        return True
    if any(m in s for m in ["0-3", "3-6", "6-9", "9-12", "12-18", "18-24", "0-6M", "6-12M", "12-18M", "18-24M"]):
        return True
    return False

def normalize_department_name(gender_val: str, size_val: str) -> str:
    if not gender_val:
        return "Unisex Kids"
    g = str(gender_val).upper().strip()
    is_baby = is_baby_size(size_val)

    if "BOY" in g or "MALE" in g or "MEN" in g:
        if "WOMEN" in g or "FEMALE" in g or "GIRL" in g:
            return "Unisex Baby" if is_baby else "Unisex Kids"
        if "MENS" in g or g == "MEN":
            return "Mens"
        return "Baby Boys" if is_baby else "Boys"

    elif "GIRL" in g or "FEMALE" in g or "WOMEN" in g:
        if "WOMENS" in g or g == "WOMEN":
            return "Womens"
        return "Baby Girls" if is_baby else "Girls"

    elif "UNISEX" in g:
        return "Unisex Baby" if is_baby else "Unisex Kids"

    return "Unisex Kids"

def normalize_target_gender(gender_val: str) -> str:
    if not gender_val:
        return "Unisex"
    g = str(gender_val).upper().strip()
    if "GIRL" in g or "FEMALE" in g or "WOMEN" in g or "WOMAN" in g:
        return "Female"
    elif "BOY" in g or "MALE" in g or "MEN" in g or "MAN" in g:
        return "Male"
    elif "UNISEX" in g:
        return "Unisex"
    return "Unisex"

def parse_bottoms_sizes(size_val: str):
    if not size_val:
        return None, None
    s = str(size_val).strip()
    
    range_match = re.match(r'^(\d+)\s*[-\s]\s*(\d+)\s*([A-Za-z]+)?$', s)
    if range_match:
        n1, n2, unit = range_match.groups()
        unit_str = "Years"
        if unit:
            u_upper = unit.upper()
            if "M" in u_upper or "MON" in u_upper:
                unit_str = "Months"
            elif "Y" in u_upper or "YR" in u_upper:
                unit_str = "Years"
        elif int(n2) > 24 or (int(n1) <= 12 and int(n2) <= 24 and int(n1) > 0 and int(n2) - int(n1) <= 6):
            unit_str = "Months"
        return f"{n1} {unit_str}", f"{n2} {unit_str}"
        
    single_match = re.match(r'^(\d+)\s*([A-Za-z]+)?$', s)
    if single_match:
        n1, unit = single_match.groups()
        unit_str = "Years"
        if unit:
            u_upper = unit.upper()
            if "M" in u_upper or "MON" in u_upper:
                unit_str = "Months"
            elif "Y" in u_upper or "YR" in u_upper:
                unit_str = "Years"
        return f"{n1} {unit_str}", None

    return s, None

class GenerationService:
    @staticmethod
    def extract_style_code(sku):
        if not sku:
            return ""
        sku_str = str(sku).strip()
        parts = [x for x in sku_str.replace("_", "-").split("-") if x]
        if parts:
            return parts[0]
        return sku_str

    @classmethod
    def generate_listings(cls, db, skus_input: str, item_directory_path: str, master_sheet_path: str, content_sheet_path: str, template_path: str, output_path: str, task_logger=None):
        """
        Main runner function to generate Amazon listing flat files.
        """
        def log(msg):
            if task_logger:
                task_logger(msg)
            else:
                logger.info(msg)

        log("📂 Reading Amazon template file...")
        meta = ExcelProcessor.parse_template(template_path)
        attributes_meta = meta["attributes"]
        ptd_mappings = meta["ptd_mappings"]
        sheet_info = meta["sheet_info"]
        
        log("📊 Loading uploaded source files...")
        item_dir = LearningEngine.load_excel_as_dicts(item_directory_path) if item_directory_path else []
        master_sheet = LearningEngine.load_excel_as_dicts(master_sheet_path) if master_sheet_path else []
        content_sheet = LearningEngine.load_excel_as_dicts(content_sheet_path) if content_sheet_path else []
        
        log(f"   Loaded {len(item_dir):,} products from Item Directory")
        log(f"   Loaded {len(content_sheet):,} rows from Content Sheet")
        
        if not item_dir:
            raise ValueError("Item Directory has no rows or could not be parsed.")
            
        input_tokens = [x.strip() for x in skus_input.replace("\n", ",").split(",") if x.strip()]
        log(f"🔍 Searching for {len(input_tokens)} item code(s)/variant(s): {', '.join(input_tokens)}")
        
        sample_row = item_dir[0]
        item_color_col = None   # e.g. "Item Color" = "PGDNJS003295-LT. BLUE"
        item_name_col = None    # e.g. "ITEM NAME"  = "PGDNJS003295"
        barcode_col = None      # e.g. "ITEM CODE"  = 8905120616853
        color_col = None        # e.g. "COLOR"      = "LT. BLUE"

        for k in sample_row.keys():
            k_clean = str(k).strip().lower()
            if k_clean in ["item color", "item_color", "item color_1"]:
                if item_color_col is None:  # prefer first occurrence
                    item_color_col = k
            elif k_clean in ["item name", "item_name"]:
                item_name_col = k
            elif k_clean in ["item code", "item_code", "itemcode"]:
                barcode_col = k
            elif k_clean in ["color", "colour"]:
                color_col = k

        # Primary match column = Item Color (contains full "STYLECODE-COLOR" string)
        # Primary style column  = ITEM NAME  (contains just "STYLECODE")
        # Child SKU to write    = Item Color value (not the barcode)
        from ..models import LearnedMapping

        # ─── PRECISION ITEM COLOR MATCHING ENGINE ───────────────────────────────
        # We match ONLY on the "Item Color" column (e.g. "PGDNJS003295-LT. BLUE").
        # A token like "PGDNJS003295-BLACK" must match ONLY rows whose Item Color
        # normalizes to exactly that string — never "PGDNJS003295-LT. BLUE".
        matched_child_items = []
        for token in input_tokens:
            token_str = str(token).strip()
            if not token_str:
                continue
            token_clean = re.sub(r'[\s]+', ' ', token_str.upper().strip())

            matches = []
            for row in item_dir:
                matched = False

                # Check 1 — Exact match on Item Color column (primary)
                if item_color_col:
                    ic_val = str(row.get(item_color_col, "") or "").strip()
                    if ic_val:
                        ic_norm = re.sub(r'[\s]+', ' ', ic_val.upper())
                        if token_clean == ic_norm:
                            matched = True

                # Check 2 — Exact match on ITEM NAME (style-only tokens like "PGDNJS003295")
                if not matched and item_name_col and "-" not in token_str:
                    in_val = str(row.get(item_name_col, "") or "").strip()
                    if in_val:
                        in_norm = re.sub(r'[\s]+', ' ', in_val.upper())
                        if token_clean == in_norm:
                            matched = True

                if matched:
                    matches.append(row)

            if matches:
                matched_child_items.extend(matches)
            else:
                log(f"⚠ No products found matching '{token}' — check spelling or Item Directory.")

        # De-duplicate by barcode (ITEM CODE) — unique per size+color row
        # DO NOT deduplicate by Item Color — that would collapse all sizes to 1
        unique_children = []
        seen_barcodes = set()
        for c in matched_child_items:
            # Use barcode as unique key; fall back to Item Color + SIZE if no barcode
            barcode_key = str(c.get(barcode_col, "") or "").strip()
            if not barcode_key:
                ic = str(c.get(item_color_col, "") or "").strip()
                sz = str(c.get("SIZE", "") or "").strip()
                barcode_key = f"{ic}__{sz}"
            if barcode_key not in seen_barcodes:
                seen_barcodes.add(barcode_key)
                unique_children.append(c)
                
        log(f"✔ Found {len(unique_children)} matching product variant(s) across all style codes.")
        if not unique_children:
            raise ValueError("No matching products found in Item Directory for the inputted SKUs.")

        learned_sku_col = None
        m_sku = db.query(LearnedMapping).filter(LearnedMapping.amazon_attribute == "contribution_sku#1.value", LearnedMapping.is_active == True).first()
        if m_sku:
            learned_sku_col = m_sku.internal_column

        # 2. Enrich child rows with joins from Master & Content sheets
        master_index = {}
        for m_row in master_sheet:
            for mk, mv in m_row.items():
                if mv is not None:
                    mv_str = str(mv).strip().lower()
                    if mv_str and mv_str not in master_index:
                        master_index[mv_str] = m_row

        content_index = {}
        for ct_row in content_sheet:
            for ck, cv in ct_row.items():
                if cv is not None:
                    cv_str = str(cv).strip().lower()
                    if cv_str and cv_str not in content_index:
                        content_index[cv_str] = ct_row

        joined_items = []
        for c_row in unique_children:
            # The "Item Color" value (e.g. "PGDNJS003295-LT. BLUE") is the child SKU
            item_color_val = str(c_row.get(item_color_col, "") or "").strip()

            # The "ITEM NAME" value (e.g. "PGDNJS003295") is the style / parent group
            style_val = str(c_row.get(item_name_col, "") or "").strip()
            if not style_val or style_val.lower() in ["(nil)", "nil", "n/a", "nan", ""]:
                # fall back to first part of Item Color
                style_val = item_color_val.split("-")[0] if "-" in item_color_val else item_color_val

            # Child SKU = Item Color (e.g. "PGDNJS003295-LT. BLUE")
            child_sku = item_color_val if item_color_val else str(c_row.get(barcode_col, "")).strip()

            style_val_lower = style_val.lower()
            child_sku_lower = child_sku.lower()

            flat_item = dict(c_row)
            # Inject canonical SKU so rule engine can use it
            flat_item["__child_sku__"] = child_sku

            # Enrich from content sheet by Item Color or style
            c_matched = (
                content_index.get(child_sku_lower)
                or content_index.get(style_val_lower)
            )
            if c_matched:
                for k, v in c_matched.items():
                    if k not in flat_item or flat_item[k] is None:
                        flat_item[k] = v

            # Enrich from master sheet
            m_matched = (
                master_index.get(child_sku_lower)
                or master_index.get(style_val_lower)
            )
            if m_matched:
                for k, v in m_matched.items():
                    if k not in flat_item or flat_item[k] is None:
                        flat_item[k] = v

            joined_items.append((child_sku, style_val, flat_item))

        # 3. Group by ITEM NAME (style code) — one parent per style, children = all requested colors
        style_groups = defaultdict(list)
        for child_sku, style, flat_data in joined_items:
            style_groups[style].append(flat_data)
            
        # 4. Generate Rows for the Amazon Template
        generated_rows = []
        
        from ..models import AdminRule, HardcodedDefault, LearnedMapping, ValueMapping
        admin_rules = db.query(AdminRule).all()
        hardcoded_defaults = db.query(HardcodedDefault).all()
        learned_mappings = db.query(LearnedMapping).all()
        value_mappings = db.query(ValueMapping).all()
        
        rules_cache = {}
        for r in admin_rules:
            key = (r.amazon_attribute, r.scope, r.scope_value)
            rules_cache[key] = r
            
        defaults_cache = {}
        for d in hardcoded_defaults:
            if d.is_active:
                defaults_cache[d.amazon_attribute] = d
                
        mappings_cache = {}
        for m in learned_mappings:
            if m.is_active:
                mappings_cache[m.amazon_attribute] = m
                
        value_mappings_cache = {}
        for v in value_mappings:
            key = (v.amazon_attribute, v.internal_value)
            value_mappings_cache[key] = v
            
        rules_lookup = {
            "admin_rules": rules_cache,
            "defaults": defaults_cache,
            "learned_mappings": mappings_cache,
            "value_mappings": value_mappings_cache
        }
        
        resolved_ptd = "SHIRT"
        ptd_default = defaults_cache.get("product_type#1.value")
        if ptd_default and ptd_default.is_active:
            resolved_ptd = ptd_default.default_value
            
        if ptd_mappings:
            if resolved_ptd not in ptd_mappings:
                available_ptds = list(ptd_mappings.keys())
                if available_ptds:
                    matched_ptd = None
                    for aptd in available_ptds:
                        if aptd.lower() in str(template_path).lower() or str(template_path).lower() in aptd.lower():
                            matched_ptd = aptd
                            break
                    resolved_ptd = matched_ptd or available_ptds[0]
            
        unlocked_attrs = ptd_mappings.get(resolved_ptd, [])
        log(f"🏷 Product Type: {resolved_ptd} — {len(unlocked_attrs)} fields unlocked for this template.")
        
        for style_code, children_data in style_groups.items():
            resolved_title = None
            resolved_desc = None
            bullet_points_count = 0
            child_variants_info = []
            
            # A. Generate Parent Row
            parent_sku = f"{style_code}-$P"
            parent_row = {}
            
            parent_row["product_type#1.value"] = resolved_ptd
            parent_row["::record_action"] = "Create or Replace (Full Update)"
            parent_row["contribution_sku#1.value"] = parent_sku
            
            parentage_attr = None
            theme_attr = None
            parent_sku_attr = None
            relationship_type_attr = None
            
            for attr in attributes_meta.keys():
                if "parentage_level" in attr:
                    parentage_attr = attr
                if "variation_theme#1.name" in attr or "variation_theme" in attr:
                    theme_attr = attr
                if "parent_sku" in attr:
                    parent_sku_attr = attr
                if "relationship_type" in attr:
                    relationship_type_attr = attr
            
            if parentage_attr:
                parent_row[parentage_attr] = "Parent"
            if theme_attr:
                parent_row[theme_attr] = "SIZE/COLOR"
                
            sample_child = children_data[0]
            
            for attr, attr_info in attributes_meta.items():
                if attr in ["product_type#1.value", "::record_action", "contribution_sku#1.value", parentage_attr, theme_attr, parent_sku_attr, relationship_type_attr]:
                    continue
                    
                is_conditional = any(attr in attrs for attrs in ptd_mappings.values())
                if is_conditional and attr not in unlocked_attrs:
                    continue
                    
                is_variation_field = any(x in attr.lower() for x in ["size", "color", "price", "product_id", "external_product_information", "barcode"])
                if is_variation_field:
                    continue
                    
                val, source_type, score = RuleEngine.resolve_attribute_value(
                    db, attr, sample_child, product_type=resolved_ptd, brand=sample_child.get("Brand"), category=sample_child.get("Category"), rules_lookup=rules_lookup
                )
                
                # Rule Overrides
                if is_brand_attribute(attr):
                    div_val = ""
                    for k, v in sample_child.items():
                        if k.strip().lower() == "division":
                            div_val = str(v).strip().upper() if v is not None else ""
                            break
                    if div_val == "FOOTWEAR":
                        val = "Toothless"
                        source_type = "override"
                    elif div_val in ["APPAREL", "ACCESSORIES"]:
                        val = "Purple United Kids"
                        source_type = "override"
                        
                elif is_color_map_attribute(attr):
                    if val is not None:
                        val = str(val).title()
                        source_type = "override"

                elif is_department_attribute(attr):
                    gender_val = ""
                    size_val = ""
                    for k, v in sample_child.items():
                        k_lower = k.strip().lower()
                        if k_lower in ["gender", "item_gender", "target_gender"]:
                            gender_val = str(v).strip() if v is not None else ""
                        elif k_lower in ["size", "footwear_size", "size_name", "item_size"]:
                            size_val = str(v).strip() if v is not None else ""
                    val = normalize_department_name(gender_val, size_val)
                    source_type = "override"

                elif is_target_gender_attribute(attr):
                    gender_val = ""
                    for k, v in sample_child.items():
                        if k.strip().lower() in ["gender", "item_gender", "target_gender"]:
                            gender_val = str(v).strip() if v is not None else ""
                            break
                    val = normalize_target_gender(gender_val)
                    source_type = "override"

                elif is_material_attribute(attr):
                    fabric_val = ""
                    for k, v in sample_child.items():
                        if k.strip().lower() in ["fabric", "fabric_type", "material", "composition", "fabric composition"]:
                            if v is not None and str(v).strip().lower() not in ["", "(nil)", "nil", "n/a", "nan"]:
                                fabric_val = str(v).strip()
                                break
                    if fabric_val:
                        val = fabric_val
                        source_type = "override"

                if val is not None:
                    if "bullet_point" in attr.lower():
                        bullet_match = re.search(r'#(\d+)\.value', attr)
                        if bullet_match:
                            bullet_idx = int(bullet_match.group(1))
                            lines = [l.strip().lstrip('*').lstrip('-').lstrip('●').lstrip('•').strip() 
                                     for l in str(val).replace('\r', '\n').split('\n') if l.strip()]
                            if len(lines) >= bullet_idx:
                                val = lines[bullet_idx - 1]
                                bullet_points_count = max(bullet_points_count, bullet_idx)
                            else:
                                val = None
                    if val is not None:
                        parent_row[attr] = val
                        if "item_name" in attr.lower():
                            resolved_title = val
                        elif "product_description" in attr.lower():
                            resolved_desc = val
                    
            generated_rows.append(parent_row)
            
            # B. Generate Child Rows
            for child_idx, child_flat in enumerate(children_data):
                child_row = {}
                # Child SKU = barcode (ITEM CODE) — unique per size+color row
                # Fall back to ItemColor-SIZE if no barcode
                barcode_val = str(child_flat.get(barcode_col, "") or "").strip()
                item_color_val_child = str(child_flat.get(item_color_col, "") or "").strip()
                size_val_child = str(child_flat.get("SIZE", "") or "").strip()
                if barcode_val:
                    child_sku_val = barcode_val
                elif item_color_val_child and size_val_child:
                    child_sku_val = f"{item_color_val_child}-{size_val_child}"
                else:
                    child_sku_val = child_flat.get("__child_sku__") or f"{style_code}-CHILD-{child_idx}"
                child_sku_val = str(child_sku_val).strip()

                child_row["product_type#1.value"] = resolved_ptd
                child_row["::record_action"] = "Create or Replace (Full Update)"
                child_row["contribution_sku#1.value"] = child_sku_val
                
                if parentage_attr:
                    child_row[parentage_attr] = "Child"
                if parent_sku_attr:
                    child_row[parent_sku_attr] = parent_sku
                if theme_attr:
                    child_row[theme_attr] = "SIZE/COLOR"
                if relationship_type_attr:
                    child_row[relationship_type_attr] = "Variation"
                    
                for attr, attr_info in attributes_meta.items():
                    if attr in [
                        "product_type#1.value", "::record_action", "contribution_sku#1.value",
                        parentage_attr, parent_sku_attr, theme_attr, relationship_type_attr
                    ]:
                        continue
                        
                    is_conditional = any(attr in attrs for attrs in ptd_mappings.values())
                    if is_conditional and attr not in unlocked_attrs:
                        continue
                        
                    val, source_type, score = RuleEngine.resolve_attribute_value(
                        db, attr, child_flat, product_type=resolved_ptd, brand=child_flat.get("Brand"), category=child_flat.get("Category"), rules_lookup=rules_lookup
                    )
                    
                    # Rule Overrides
                    if is_brand_attribute(attr):
                        div_val = ""
                        for k, v in child_flat.items():
                            if k.strip().lower() == "division":
                                div_val = str(v).strip().upper() if v is not None else ""
                                break
                        if div_val == "FOOTWEAR":
                            val = "Toothless"
                            source_type = "override"
                        elif div_val in ["APPAREL", "ACCESSORIES"]:
                            val = "Purple United Kids"
                            source_type = "override"
                            
                    elif is_epi_entity_attribute(attr):
                        val = "HSN Code"
                        source_type = "override"
                        
                    elif is_epi_value_attribute(attr):
                        hs_val = ""
                        for k, v in child_flat.items():
                            if k.strip().lower() in ["hs code", "hscode", "hsn code", "hsncode"]:
                                hs_val = str(v).strip() if v is not None else ""
                                break
                        if hs_val:
                            val = hs_val
                            source_type = "override"
                            
                    elif is_color_name_attribute(attr):
                        c_val = ""
                        for k, v in child_flat.items():
                            if k.strip().lower() in ["color", "color_name", "item_color", "item color"]:
                                c_val = str(v).strip() if v is not None else ""
                                break
                        if c_val:
                            val = c_val
                            source_type = "override"
                            
                    elif is_color_map_attribute(attr):
                        c_val = ""
                        for k, v in child_flat.items():
                            if k.strip().lower() in ["color", "color_name", "item_color", "item color"]:
                                c_val = str(v).strip() if v is not None else ""
                                break
                        if c_val:
                            val = c_val.title()
                            source_type = "override"

                    elif is_department_attribute(attr):
                        gender_val = ""
                        size_val = ""
                        for k, v in child_flat.items():
                            k_lower = k.strip().lower()
                            if k_lower in ["gender", "item_gender", "target_gender"]:
                                if v is not None and str(v).strip().lower() not in ["", "(nil)", "nil", "n/a", "nan"]:
                                    gender_val = str(v).strip()
                            elif k_lower in ["size", "footwear_size", "size_name", "item_size"]:
                                if v is not None and str(v).strip().lower() not in ["", "(nil)", "nil", "n/a", "nan"]:
                                    size_val = str(v).strip()
                        val = normalize_department_name(gender_val, size_val)
                        source_type = "override"

                    elif is_target_gender_attribute(attr):
                        gender_val = ""
                        for k, v in child_flat.items():
                            if k.strip().lower() in ["gender", "item_gender", "target_gender"]:
                                if v is not None and str(v).strip().lower() not in ["", "(nil)", "nil", "n/a", "nan"]:
                                    gender_val = str(v).strip()
                                    break
                        val = normalize_target_gender(gender_val)
                        source_type = "override"

                    elif is_size_value_attribute(attr):
                        size_val = ""
                        for k, v in child_flat.items():
                            if k.strip().lower() in ["size", "footwear_size", "size_name", "item_size"]:
                                if v is not None and str(v).strip().lower() not in ["", "(nil)", "nil", "n/a", "nan"]:
                                    size_val = str(v).strip()
                                    break
                        v_val, _ = parse_bottoms_sizes(size_val)
                        if v_val:
                            val = v_val
                            source_type = "override"

                    elif is_size_range_attribute(attr):
                        size_val = ""
                        for k, v in child_flat.items():
                            if k.strip().lower() in ["size", "footwear_size", "size_name", "item_size"]:
                                if v is not None and str(v).strip().lower() not in ["", "(nil)", "nil", "n/a", "nan"]:
                                    size_val = str(v).strip()
                                    break
                        _, r_val = parse_bottoms_sizes(size_val)
                        if r_val:
                            val = r_val
                            source_type = "override"

                    elif is_material_attribute(attr):
                        fabric_val = ""
                        for k, v in child_flat.items():
                            if k.strip().lower() in ["fabric", "fabric_type", "material", "composition", "fabric composition"]:
                                if v is not None and str(v).strip().lower() not in ["", "(nil)", "nil", "n/a", "nan"]:
                                    fabric_val = str(v).strip()
                                    break
                        if fabric_val:
                            val = fabric_val
                            source_type = "override"

                    if val is not None:
                        if "bullet_point" in attr.lower():
                            bullet_match = re.search(r'#(\d+)\.value', attr)
                            if bullet_match:
                                bullet_idx = int(bullet_match.group(1))
                                lines = [l.strip().lstrip('*').lstrip('-').lstrip('●').lstrip('•').strip() 
                                         for l in str(val).replace('\r', '\n').split('\n') if l.strip()]
                                if len(lines) >= bullet_idx:
                                    val = lines[bullet_idx - 1]
                                else:
                                    val = None
                        if val is not None:
                            child_row[attr] = val
                        
                generated_rows.append(child_row)
                
                child_size = "N/A"
                child_color = "N/A"
                for k, v in child_flat.items():
                    k_lower = k.lower()
                    if v is not None:
                        if k_lower in ["size", "footwear_size", "size_name", "item_size"]:
                            child_size = str(v)
                        elif k_lower in ["color", "color_name", "color_map"]:
                            child_color = str(v)
                child_variants_info.append({
                    "sku": child_sku_val,
                    "size": child_size,
                    "color": child_color
                })

            log(f"✅ Resolved & Generated Listing for Style '{style_code}':")
            if resolved_title:
                log(f"   • Product Title: \"{resolved_title}\"")
            else:
                log(f"   • Product Title: (Not found in Content Sheet)")
                
            if resolved_desc:
                desc_summary = resolved_desc[:120] + ("..." if len(resolved_desc) > 120 else "")
                log(f"   • Description: \"{desc_summary}\"")
            else:
                log(f"   • Description: (Not found in Content Sheet)")
                
            log(f"   • Bullet Points: Loaded {bullet_points_count} points")
            log(f"   • Child Variants ({len(child_variants_info)} items):")
            for c_info in child_variants_info:
                log(f"     - SKU: {c_info['sku']} (Size: {c_info['size']}, Color: {c_info['color']})")
            log("")

        log("🔎 Validating all generated rows against Amazon requirements...")
        val_report = ValidationService.validate_listings(generated_rows, attributes_meta, ptd_mappings)
        
        log("💾 Writing populated rows to Amazon Excel template...")
        ExcelProcessor.write_template(template_path, output_path, generated_rows, sheet_info)
        
        log(f"🎉 Success! Amazon listing generated at: {output_path}")
        return {
            "output_path": output_path,
            "total_rows": len(generated_rows),
            "parent_styles": len(style_groups),
            "validation_report": val_report
        }
