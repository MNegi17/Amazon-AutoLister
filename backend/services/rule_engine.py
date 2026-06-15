from ..models import AdminRule, HardcodedDefault, LearnedMapping, ValueMapping

class RuleEngine:
    @classmethod
    def resolve_attribute_value(cls, db, amazon_attr: str, item_data: dict, product_type: str = None, brand: str = None, category: str = None) -> tuple:
        """
        Resolves the value of an Amazon attribute for a given item.
        Returns:
            tuple: (resolved_value, source_type, confidence_score)
                - resolved_value: The final value to write.
                - source_type: 'admin_rule', 'hardcoded_default', 'learned_mapping', 'value_mapping', or 'not_found'.
                - confidence_score: Float between 0.0 and 1.0.
        """
        # 1. Evaluate Admin Rules (Scope Specificity: Product Type > Brand > Category > Global)
        # Search for Product Type rule
        if product_type:
            rule = db.query(AdminRule).filter(
                AdminRule.amazon_attribute == amazon_attr,
                AdminRule.scope == "product_type",
                AdminRule.scope_value == product_type
            ).first()
            if rule:
                return rule.rule_value, "admin_rule", 1.0
                
        # Search for Brand rule
        if brand:
            rule = db.query(AdminRule).filter(
                AdminRule.amazon_attribute == amazon_attr,
                AdminRule.scope == "brand",
                AdminRule.scope_value == brand
            ).first()
            if rule:
                return rule.rule_value, "admin_rule", 1.0
                
        # Search for Category rule
        if category:
            rule = db.query(AdminRule).filter(
                AdminRule.amazon_attribute == amazon_attr,
                AdminRule.scope == "category",
                AdminRule.scope_value == category
            ).first()
            if rule:
                return rule.rule_value, "admin_rule", 1.0

        # Search for Global rule
        rule = db.query(AdminRule).filter(
            AdminRule.amazon_attribute == amazon_attr,
            AdminRule.scope == "global"
        ).first()
        if rule:
            return rule.rule_value, "admin_rule", 1.0

        # 2. Evaluate Hardcoded Admin Defaults
        default_cfg = db.query(HardcodedDefault).filter(
            HardcodedDefault.amazon_attribute == amazon_attr,
            HardcodedDefault.is_active == True
        ).first()
        if default_cfg:
            return default_cfg.default_value, "hardcoded_default", 1.0

        # 3. Evaluate Learned Column Mappings & Value Translations
        mapping = db.query(LearnedMapping).filter(
            LearnedMapping.amazon_attribute == amazon_attr,
            LearnedMapping.is_active == True
        ).first()
        
        if mapping:
            internal_col = mapping.internal_column
            # internal_col format is usually "source_name.column_name" e.g., "item_directory.Fabric"
            # or just "column_name" if loaded directly
            col_key = internal_col
            if "." in internal_col:
                parts = internal_col.split(".", 1)
                col_key = parts[1] # get the actual column name
                
            raw_val = item_data.get(col_key)
            if raw_val is None:
                # Fallback to key containing the suffix or prefix
                for k, v in item_data.items():
                    if k.lower() == col_key.lower():
                        raw_val = v
                        break
            
            if raw_val is not None:
                raw_val_str = str(raw_val).strip()
                # Check for value translation (e.g. size/color maps)
                translation = db.query(ValueMapping).filter(
                    ValueMapping.amazon_attribute == amazon_attr,
                    ValueMapping.internal_value == raw_val_str
                ).first()
                
                if translation:
                    return translation.amazon_value, "value_mapping", translation.confidence_score
                    
                # Return direct copy value
                return raw_val_str, "learned_mapping", mapping.confidence_score

        # 4. Name-based Fallbacks for Title, Description and Bullet Points
        attr_lower = amazon_attr.lower()
        if "item_name" in attr_lower or "title" in attr_lower:
            for alt_k in ["Amazon Title", "Title", "Item Name", "item_name", "item name", "D2C Title", "ITEM DESCRIPTION"]:
                if item_data.get(alt_k) is not None and str(item_data.get(alt_k)).strip() != "":
                    return str(item_data.get(alt_k)).strip(), "name_fallback", 0.9
        elif "description" in attr_lower:
            for alt_k in ["Description", "product_description", "description", "Product Description", "ITEM DESCRIPTION"]:
                if item_data.get(alt_k) is not None and str(item_data.get(alt_k)).strip() != "":
                    return str(item_data.get(alt_k)).strip(), "name_fallback", 0.9
        elif "bullet_point" in attr_lower:
            for alt_k in ["Bullet Points", "bullet_point", "bullet points", "Bullet Point", "bullet point"]:
                if item_data.get(alt_k) is not None and str(item_data.get(alt_k)).strip() != "":
                    return str(item_data.get(alt_k)).strip(), "name_fallback", 0.9

        return None, "not_found", 0.0
