#!/usr/bin/env python3
"""
Write script: Generate spec variants for each slot.
"""
import hashlib
import math
import random
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import click
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from golden.lib.bands import BAND_RANGES, count_tokens
from golden.lib.io_utils import read_json, read_text, write_jsonl


class SpecWriter:
    """Deterministic spec writer for generating variants."""
    
    def __init__(self, seed: int = 2025):
        """Initialize the spec writer with templates and seed."""
        self.seed = seed
        self.rng = random.Random(seed)
        
        # Load templates
        templates_dir = Path(__file__).parent.parent / "golden" / "templates"
        self.h2_sections = read_text(templates_dir / "h2_sections.md")
        self.acl_snippet = read_text(templates_dir / "acl_snippet.txt")
        
        with open(templates_dir / "archetype_kits.yaml", "r") as f:
            self.archetype_kits = yaml.safe_load(f)
            
        with open(templates_dir / "wording_banks.yaml", "r") as f:
            self.wording_banks = yaml.safe_load(f)
    
    def _get_deterministic_seed(self, slot_id: str, variant: int) -> int:
        """Generate a deterministic seed from slot_id and variant."""
        seed_str = f"{self.seed}|{slot_id}|{variant}"
        return int(hashlib.sha256(seed_str.encode()).hexdigest()[:8], 16)
    
    def _get_platform_config(self, archetype: str, complexity: str) -> Dict:
        """Get platform configuration for an archetype and complexity."""
        return {
            "name": "replit",
            "server": self.archetype_kits[archetype][complexity]["server"],
            "bind": "0.0.0.0" if self.archetype_kits[archetype][complexity]["server"] else None
        }
    
    def _generate_vision_section(self, seed: int, archetype: str, complexity: str) -> str:
        """Generate the Vision section."""
        rng = random.Random(seed)
        
        # Select a vision statement template
        vision_template = rng.choice(self.wording_banks["vision_statements"])
        
        # Generate content based on archetype and complexity
        lines = [
            "## Vision",
            "",
            f"{vision_template} for {archetype} management.",
            "",
            f"This {complexity} {archetype} application will provide users with a streamlined way to "
        ]
        
        # Add archetype-specific content
        if archetype == "blog":
            lines.append("create, publish, and manage blog content with ease.")
        elif archetype == "guestbook":
            lines.append("leave messages, comments, and interact with site visitors.")
        elif archetype == "chat":
            lines.append("communicate in real-time with other users in a structured environment.")
        elif archetype == "notes":
            lines.append("create, organize, and retrieve personal notes efficiently.")
        elif archetype == "dashboard":
            lines.append("visualize and analyze key metrics and data points.")
        elif archetype == "store":
            lines.append("browse products, manage a shopping cart, and complete purchases.")
        elif archetype == "gallery":
            lines.append("showcase and organize visual content in an appealing way.")
        
        # Add complexity-specific content
        if complexity == "MVP":
            lines.append("")
            lines.append("The initial version will focus on core functionality while maintaining a clean, intuitive interface.")
        else:  # Pro
            lines.append("")
            lines.append("This professional version includes advanced features, robust security, and enhanced user experience.")
        
        return "\n".join(lines)
    
    def _generate_tech_stack_section(self, seed: int, platform: Dict) -> str:
        """Generate the Tech Stack section."""
        rng = random.Random(seed)
        
        # Select intro template
        intro = rng.choice(self.wording_banks["tech_stack_intros"])
        
        # Select technologies based on platform
        frontend = rng.choice(self.wording_banks["tech_options"]["frontend"])
        backend = rng.choice(self.wording_banks["tech_options"]["backend"]) if platform["server"] else None
        database = rng.choice(self.wording_banks["tech_options"]["database"]) if platform["server"] else None
        deployment = rng.choice(self.wording_banks["tech_options"]["deployment"])
        
        lines = [
            "## Tech Stack",
            "",
            intro,
            "",
            f"- **Frontend**: {frontend}"
        ]
        
        if backend:
            lines.append(f"- **Backend**: {backend}")
        
        if database:
            lines.append(f"- **Database**: {database}")
        
        lines.append(f"- **Deployment**: {deployment}")
        
        if platform["server"]:
            lines.append(f"- **Hosting**: Replit with server binding to {platform['bind']}")
        else:
            # Avoid using banned network terms for static hosting
            lines.append("- **Hosting**: Replit static site hosting")
        
        return "\n".join(lines)
    
    def _generate_data_models_section(self, seed: int, archetype: str, complexity: str) -> str:
        """Generate the Data Models section."""
        rng = random.Random(seed)
        
        # Select intro template
        intro = rng.choice(self.wording_banks["data_model_intros"])
        
        lines = [
            "## Data Models",
            "",
            intro,
            ""
        ]
        
        # Define models based on archetype
        models = []
        if archetype == "blog":
            models.append("**User**: id, username, email, password_hash, created_at")
            models.append("**Post**: id, title, content, author_id, created_at, updated_at")
            models.append("**Comment**: id, post_id, author_id, content, created_at")
            
            if complexity == "Pro":
                models.append("**Category**: id, name, description")
                models.append("**Tag**: id, name")
                models.append("**PostTag**: post_id, tag_id")
        
        elif archetype == "guestbook":
            models.append("**Entry**: id, author_name, email, content, created_at")
            
            if complexity == "Pro":
                models.append("**User**: id, username, email, password_hash, created_at")
                models.append("**Media**: id, entry_id, url, type, created_at")
        
        elif archetype == "chat":
            models.append("**User**: id, username, email, password_hash, created_at, last_active")
            models.append("**Message**: id, sender_id, content, created_at")
            
            if complexity == "Pro":
                models.append("**Room**: id, name, description, created_at")
                models.append("**RoomMember**: room_id, user_id, joined_at")
                models.append("**DirectMessage**: id, sender_id, recipient_id, content, created_at")
        
        elif archetype == "notes":
            if complexity == "MVP":
                models.append("**Note**: id, title, content, created_at, updated_at")
            else:
                models.append("**User**: id, username, email, password_hash, created_at")
                models.append("**Note**: id, user_id, title, content, created_at, updated_at")
                models.append("**Category**: id, user_id, name")
                models.append("**NoteCategory**: note_id, category_id")
        
        elif archetype == "dashboard":
            models.append("**User**: id, username, email, password_hash, created_at")
            models.append("**Dashboard**: id, user_id, name, layout, created_at")
            models.append("**Widget**: id, dashboard_id, type, data_source, position, size")
            
            if complexity == "Pro":
                models.append("**DataSource**: id, name, connection_string, query, refresh_rate")
                models.append("**Report**: id, user_id, name, description, query, created_at")
        
        elif archetype == "store":
            models.append("**Product**: id, name, description, price, image_url, stock")
            models.append("**Cart**: id, session_id, created_at")
            models.append("**CartItem**: id, cart_id, product_id, quantity")
            models.append("**Order**: id, customer_name, email, address, status, created_at")
            
            if complexity == "Pro":
                models.append("**User**: id, username, email, password_hash, created_at")
                models.append("**Category**: id, name, description")
                models.append("**ProductCategory**: product_id, category_id")
                models.append("**Payment**: id, order_id, amount, provider, status, created_at")
        
        elif archetype == "gallery":
            if complexity == "MVP":
                models.append("**Image**: id, title, description, url, created_at")
                models.append("**Tag**: id, name")
                models.append("**ImageTag**: image_id, tag_id")
            else:
                models.append("**User**: id, username, email, password_hash, created_at")
                models.append("**Image**: id, user_id, title, description, url, created_at")
                models.append("**Collection**: id, user_id, name, description, created_at")
                models.append("**CollectionImage**: collection_id, image_id")
                models.append("**Comment**: id, image_id, user_id, content, created_at")
        
        # Add models to lines
        for model in models:
            lines.append(f"- {model}")
        
        return "\n".join(lines)
    
    def _generate_pages_routes_section(self, seed: int, archetype: str, complexity: str) -> str:
        """Generate the Pages & Routes section."""
        rng = random.Random(seed)
        
        # Select intro template
        intro = rng.choice(self.wording_banks["routes_intros"])
        
        lines = [
            "## Pages & Routes",
            "",
            intro,
            ""
        ]
        
        # Get pages from archetype kits
        pages = self.archetype_kits[archetype][complexity]["pages"]
        
        # Add pages to lines
        for page in pages:
            route = page.lower().replace(" ", "-")
            if page == "Home":
                lines.append(f"- **{page}**: `/` - The main landing page")
            else:
                lines.append(f"- **{page}**: `/{route}` - {self._generate_page_description(page, archetype)}")
        
        return "\n".join(lines)
    
    def _generate_page_description(self, page: str, archetype: str) -> str:
        """Generate a description for a page."""
        descriptions = {
            "Post Detail": "Displays a single blog post with comments",
            "About": "Information about the blog and its authors",
            "Author Profiles": "Details about each author",
            "Categories": "Browse posts by category",
            "Search": "Search for posts by keyword",
            "Admin Dashboard": "Manage blog content and settings",
            "Entry Form": "Form for submitting new guestbook entries",
            "User Profiles": "View user profile information",
            "Admin Panel": "Moderate entries and manage users",
            "Chat Room": "Main chat interface",
            "Login": "User authentication page",
            "Chat Rooms": "List of available chat rooms",
            "Direct Messages": "Private conversations between users",
            "Settings": "User preferences and account settings",
            "Notes List": "Overview of all notes",
            "Note Editor": "Create and edit notes",
            "Categories": "Organize notes by category",
            "Sync Status": "View synchronization status",
            "Overview": "Main dashboard view",
            "Data View": "Detailed data visualization",
            "Detailed Analytics": "In-depth data analysis",
            "Reports": "Generated reports and exports",
            "User Management": "Manage user accounts and permissions",
            "System Settings": "Configure system parameters",
            "Product List": "Browse available products",
            "Product Detail": "View detailed product information",
            "Cart": "Review items before checkout",
            "Checkout": "Complete purchase process",
            "Product Categories": "Browse products by category",
            "User Account": "Manage account details",
            "Order History": "View past orders",
            "Gallery Grid": "Grid layout of images",
            "Image View": "Detailed view of a single image",
            "Image Detail": "Expanded image with metadata",
            "Collections": "Grouped sets of images",
            "Upload": "Add new images to the gallery"
        }
        
        return descriptions.get(page, f"{page} page")
    
    def _generate_feature_plan_section(self, seed: int, archetype: str, complexity: str) -> str:
        """Generate the Feature Plan section."""
        rng = random.Random(seed)
        
        # Select intro template
        intro = rng.choice(self.wording_banks["feature_plan_intros"])
        
        lines = [
            "## Feature Plan",
            "",
            intro,
            ""
        ]
        
        # Get features from archetype kits
        features = self.archetype_kits[archetype][complexity]["features"]
        
        # Add features to lines
        for feature in features:
            lines.append(f"- {feature}")
        
        # Add ACL snippet
        lines.extend(["", self.acl_snippet])
        
        return "\n".join(lines)
    
    def _generate_nfr_section(self, seed: int) -> str:
        """Generate the NFR & SLOs section."""
        rng = random.Random(seed)
        
        # Select intro template
        intro = rng.choice(self.wording_banks["nfr_intros"])
        
        lines = [
            "## NFR & SLOs",
            "",
            intro,
            ""
        ]
        
        # Select NFRs from each category
        categories = ["performance", "security", "reliability", "usability", "maintainability"]
        for category in categories:
            # Capitalize category name
            category_name = category.capitalize()
            lines.append(f"**{category_name}:**")
            
            # Select 2 requirements from this category
            requirements = rng.sample(self.wording_banks["nfr_categories"][category], 2)
            for req in requirements:
                lines.append(f"- {req}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _adjust_length_to_band(self, spec: str, target_band: str, seed: int) -> str:
        """Adjust spec length to fit within target band."""
        rng = random.Random(seed)
        token_count = count_tokens(spec)
        min_tokens, max_tokens = BAND_RANGES[target_band]
        
        if min_tokens <= token_count <= max_tokens:
            # Already in target band
            return spec
        
        if token_count < min_tokens:
            # Need to pad
            return self._pad_spec(spec, min_tokens - token_count, rng)
        else:
            # Need to trim
            return self._trim_spec(spec, token_count - max_tokens, rng)
    
    def _pad_spec(self, spec: str, tokens_to_add: int, rng: random.Random) -> str:
        """Pad spec with additional content to reach target length."""
        sections = re.split(r'^##\s+', spec, flags=re.MULTILINE)
        header = sections[0]  # Empty string before first header
        content_sections = sections[1:]
        
        # Determine how many sentences to add
        avg_tokens_per_sentence = 15
        sentences_to_add = math.ceil(tokens_to_add / avg_tokens_per_sentence)
        
        # Get padding sentences based on length needed
        if tokens_to_add > 100:
            padding_sentences = rng.sample(
                self.wording_banks["padding_sentences"]["extended"], 
                min(sentences_to_add, len(self.wording_banks["padding_sentences"]["extended"]))
            )
        else:
            padding_sentences = rng.sample(
                self.wording_banks["padding_sentences"]["short"],
                min(sentences_to_add, len(self.wording_banks["padding_sentences"]["short"]))
            )
        
        # Distribute padding across sections
        padded_sections = []
        for i, section in enumerate(content_sections):
            section_name, section_content = section.split("\n", 1)
            
            # Add padding at the end of the section
            if i < len(padding_sentences):
                section_content += f"\n\n{padding_sentences[i]}"
            
            padded_sections.append(f"{section_name}\n{section_content}")
        
        # Reconstruct the spec
        padded_spec = header + "## " + "## ".join(padded_sections)
        
        # If we still need more padding, add remaining sentences to the last section
        remaining_sentences = padding_sentences[len(content_sections):]
        if remaining_sentences:
            padding_text = "\n\n" + "\n\n".join(remaining_sentences)
            padded_spec += padding_text
        
        return padded_spec
    
    def _trim_spec(self, spec: str, tokens_to_remove: int, rng: random.Random) -> str:
        """Trim spec to reduce length."""
        # Split into sections
        sections = re.split(r'^##\s+', spec, flags=re.MULTILINE)
        header = sections[0]  # Empty string before first header
        content_sections = sections[1:]
        
        # Find non-essential sentences to remove
        trimmed_sections = []
        tokens_removed = 0
        
        for section in content_sections:
            # Make sure we have content after the section name
            if "\n" not in section:
                section = section + "\n"
                
            section_name, section_content = section.split("\n", 1)
            
            # Don't trim ACL section in Feature Plan
            if section_name.strip() == "Feature Plan" and "### Access Control" in section_content:
                trimmed_sections.append(f"{section_name}\n{section_content}")
                continue
            
            # Split into sentences
            sentences = re.split(r'(?<=[.!?])\s+', section_content)
            
            # Keep essential sentences (first and last in each paragraph)
            essential_indices = set()
            paragraph_start = 0
            
            for i, sentence in enumerate(sentences):
                if not sentence.strip():
                    # Empty line indicates paragraph break
                    if paragraph_start < i - 1:
                        essential_indices.add(paragraph_start)
                        essential_indices.add(i - 1)
                    paragraph_start = i + 1
            
            # Add last paragraph
            if paragraph_start < len(sentences) - 1:
                essential_indices.add(paragraph_start)
                essential_indices.add(len(sentences) - 1)
            
            # Remove non-essential sentences until we've removed enough tokens
            non_essential = [i for i in range(len(sentences)) if i not in essential_indices]
            rng.shuffle(non_essential)
            
            kept_sentences = list(sentences)
            for i in non_essential:
                if tokens_removed >= tokens_to_remove:
                    break
                
                sentence = sentences[i]
                sentence_tokens = len(tokenize_text(sentence))
                
                if tokens_removed + sentence_tokens <= tokens_to_remove:
                    kept_sentences[i] = ""
                    tokens_removed += sentence_tokens
            
            # Reconstruct section content
            trimmed_content = " ".join(s for s in kept_sentences if s)
            # Ensure there's at least some content in each section
            if not trimmed_content.strip():
                trimmed_content = "This section provides essential information."
            
            trimmed_sections.append(f"{section_name}\n{trimmed_content}")
        
        # Reconstruct the spec
        return header + "## " + "## ".join(trimmed_sections)
    
    def generate_spec(self, slot: Dict, variant: int, target_band: str) -> Dict:
        """
        Generate a spec variant for a slot.
        
        Args:
            slot: Slot dictionary
            variant: Variant number
            target_band: Target length band (SHORT, STANDARD, EXTENDED)
        
        Returns:
            Dictionary with spec and metadata
        """
        # Generate deterministic seed for this variant
        seed = self._get_deterministic_seed(slot["slot_id"], variant)
        
        # Get archetype and complexity
        archetype = slot["archetype"]
        complexity = slot["complexity"]
        
        # Get platform configuration
        platform = self._get_platform_config(archetype, complexity)
        
        # Generate sections
        vision = self._generate_vision_section(seed + 1, archetype, complexity)
        tech_stack = self._generate_tech_stack_section(seed + 2, platform)
        data_models = self._generate_data_models_section(seed + 3, archetype, complexity)
        pages_routes = self._generate_pages_routes_section(seed + 4, archetype, complexity)
        feature_plan = self._generate_feature_plan_section(seed + 5, archetype, complexity)
        nfr = self._generate_nfr_section(seed + 6)
        
        # Ensure all sections are present
        sections = [vision, tech_stack, data_models, pages_routes, feature_plan, nfr]
        
        # Check if any section is empty or missing
        for i, section in enumerate(sections):
            if not section or not section.strip():
                # Regenerate the missing section
                section_names = ["Vision", "Tech Stack", "Data Models", "Pages & Routes", "Feature Plan", "NFR & SLOs"]
                print(f"Warning: Missing {section_names[i]} section for {slot['slot_id']}__v{variant:02d}. Regenerating.")
                
                # Regenerate the section with a different seed
                if i == 0:
                    sections[i] = self._generate_vision_section(seed + 100 + i, archetype, complexity)
                elif i == 1:
                    sections[i] = self._generate_tech_stack_section(seed + 100 + i, platform)
                elif i == 2:
                    sections[i] = self._generate_data_models_section(seed + 100 + i, archetype, complexity)
                elif i == 3:
                    sections[i] = self._generate_pages_routes_section(seed + 100 + i, archetype, complexity)
                elif i == 4:
                    sections[i] = self._generate_feature_plan_section(seed + 100 + i, archetype, complexity)
                elif i == 5:
                    sections[i] = self._generate_nfr_section(seed + 100 + i)
        
        # Combine sections
        spec = "\n\n".join(sections)
        
        # Adjust length to target band
        spec = self._adjust_length_to_band(spec, target_band, seed + 7)
        
        # Create candidate_id
        candidate_id = f"{slot['slot_id']}__v{variant:02d}"
        
        # Create result
        result = {
            "slot_id": slot["slot_id"],
            "candidate_id": candidate_id,
            "archetype": archetype,
            "complexity": complexity,
            "locale": slot["locale"],
            "rep": slot["rep"],
            "seq": slot["seq"],
            "length_band": target_band,
            "platform": platform,
            "spec": spec
        }
        
        return result


def determine_band_distribution(slots: List[Dict]) -> Dict[str, List[str]]:
    """
    Determine target band distribution for slots.
    
    Args:
        slots: List of slot dictionaries
    
    Returns:
        Dict mapping slot_id to target band
    """
    # Group slots by stratum
    strata = {}
    for slot in slots:
        key = f"{slot['archetype']}-{slot['complexity']}-{slot['locale']}"
        if key not in strata:
            strata[key] = []
        strata[key].append(slot)
    
    # For each stratum, assign bands
    # Target: 1 SHORT, 3 STANDARD, 1 EXTENDED per stratum
    band_assignments = {}
    for stratum_slots in strata.values():
        # Sort by slot_id for determinism
        stratum_slots.sort(key=lambda x: x["slot_id"])
        
        # Assign bands
        for i, slot in enumerate(stratum_slots):
            if i == 0:
                band = "SHORT"
            elif i == 4:
                band = "EXTENDED"
            else:
                band = "STANDARD"
            
            band_assignments[slot["slot_id"]] = band
    
    return band_assignments


def generate_variants(
    slots: List[Dict], 
    oversub_factor: float, 
    seed: int
) -> List[Dict]:
    """
    Generate variants for each slot.
    
    Args:
        slots: List of slot dictionaries
        oversub_factor: Oversubscription factor
        seed: Random seed
    
    Returns:
        List of variant dictionaries
    """
    # Determine band distribution
    band_assignments = determine_band_distribution(slots)
    
    # Initialize spec writer
    writer = SpecWriter(seed)
    
    # Generate variants
    variants = []
    for slot in slots:
        # Calculate number of variants for this slot
        num_variants = math.ceil(oversub_factor)
        
        # Get target band for this slot
        target_band = band_assignments[slot["slot_id"]]
        
        # Generate variants
        for variant in range(1, num_variants + 1):
            spec = writer.generate_spec(slot, variant, target_band)
            variants.append(spec)
    
    return variants


@click.command()
@click.option("--in", "input_file", required=True, help="Input JSON file path")
@click.option("--out", required=True, help="Output JSONL file path")
@click.option("--oversub", type=float, default=1.2, help="Oversubscription factor")
@click.option("--seed", type=int, default=2025, help="Random seed")
def main(input_file: str, out: str, oversub: float, seed: int):
    """Generate spec variants for each slot."""
    slots = read_json(input_file)
    variants = generate_variants(slots, oversub, seed)
    write_jsonl(out, variants)
    print(f"Generated {len(variants)} variants for {len(slots)} slots")
    print(f"Wrote output to {out}")


if __name__ == "__main__":
    main()
