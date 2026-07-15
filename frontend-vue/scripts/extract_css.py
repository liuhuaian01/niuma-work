#!/usr/bin/env python3
"""
Extract CSS from niuma-neon-pulse-prototype.html and split into Vue-compatible files.

Strategy:
  1. Read the entire <style> block (line 7-11132)
  2. Output as a single comprehensive CSS file for Vue
  3. Also generate a diff report of what's missing from existing Vue CSS files
"""
import re
import os

PROTOTYPE_PATH = r'E:\05-超级牛马\super-niuma\frontend\niuma-neon-pulse-prototype.html'
VUE_CSS_DIR = r'E:\05-超级牛马\super-niuma\frontend-vue\public\css'
OUTPUT_FILE = r'E:\05-超级牛马\super-niuma\frontend-vue\public\css\prototype-design-system.css'

def extract_css():
    """Extract the entire CSS block from the prototype."""
    with open(PROTOTYPE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find <style> and </style>
    style_start = content.find('<style>')
    style_end = content.find('</style>')
    
    if style_start == -1 or style_end == -1:
        print("ERROR: Could not find <style> tags")
        return None
    
    # Extract CSS content (excluding the <style> tags)
    css_content = content[style_start + 7:style_end]
    
    # Clean up: remove leading/trailing whitespace lines
    lines = css_content.split('\n')
    # Remove first empty line
    while lines and not lines[0].strip():
        lines.pop(0)
    # Remove trailing empty lines
    while lines and not lines[-1].strip():
        lines.pop()
    
    css = '\n'.join(lines)
    print(f"[OK] Extracted {len(css)} chars, {len(lines)} lines of CSS")
    return css


def split_css_blocks(css):
    """Split CSS into logical blocks based on section headers."""
    blocks = []
    lines = css.split('\n')
    
    current_block = []
    current_header = "ROOT"
    
    for line in lines:
        # Detect section headers (CSS comments with === or ---)
        stripped = line.strip()
        if (stripped.startswith('/* ===') or 
            stripped.startswith('/* ---') or
            stripped.startswith('/* ──')):
            if current_block and any(l.strip() and not l.strip().startswith('/*') for l in current_block):
                blocks.append((current_header, '\n'.join(current_block)))
            current_block = [line]
            current_header = stripped
        else:
            current_block.append(line)
    
    # Don't forget the last block
    if current_block and any(l.strip() and not l.strip().startswith('/*') for l in current_block):
        blocks.append((current_header, '\n'.join(current_block)))
    
    print(f"[OK] Split into {len(blocks)} blocks")
    return blocks


def compare_with_vue(blocks):
    """Compare each block with existing Vue CSS to identify gaps."""
    vue_files = {}
    for fname in ['design-tokens.css', 'chat-components.css', 'components-base.css', 'enhancements.css', 'compat.css']:
        path = os.path.join(VUE_CSS_DIR, fname)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                vue_files[fname] = len(f.read())
    
    # Also check token sub-files
    token_dir = os.path.join(VUE_CSS_DIR, 'tokens')
    for fname in os.listdir(token_dir):
        if fname.endswith('.css'):
            path = os.path.join(token_dir, fname)
            with open(path, 'r', encoding='utf-8') as f:
                vue_files[f'tokens/{fname}'] = len(f.read())
    
    themes_dir = os.path.join(token_dir, 'themes')
    if os.path.exists(themes_dir):
        for fname in os.listdir(themes_dir):
            if fname.endswith('.css'):
                path = os.path.join(themes_dir, fname)
                with open(path, 'r', encoding='utf-8') as f:
                    vue_files[f'tokens/themes/{fname}'] = len(f.read())
    
    total_vue = sum(vue_files.values())
    
    print(f"\n[STATS] Vue CSS total: {total_vue:,} chars across {len(vue_files)} files")
    print(f"[STATS] Prototype CSS total: {sum(len(b[1]) for b in blocks):,} chars across {len(blocks)} blocks")
    print(f"[STATS] Gap: {(sum(len(b[1]) for b in blocks) - total_vue):,} chars ({total_vue/sum(len(b[1]) for b in blocks)*100:.0f}% coverage)")
    
    return vue_files


def main():
    print("=" * 60)
    print("CSS Extraction: niuma-neon-pulse-prototype.html -> Vue")
    print("=" * 60)
    
    # Step 1: Extract CSS
    css = extract_css()
    if not css:
        return
    
    # Step 2: Split into blocks
    blocks = split_css_blocks(css)
    
    # Step 3: Compare with Vue
    compare_with_vue(blocks)
    
    # Step 4: Save the full prototype CSS as a single file
    header = """/* ============================================================
 * PROTOTYPE DESIGN SYSTEM — Extracted from niuma-neon-pulse-prototype.html
 * This file contains the COMPLETE CSS from the HTML prototype.
 * It is loaded AFTER the existing Vue CSS files to fill gaps.
 * 
 * Generated: 2026-07-13
 * Blocks: {block_count}  |  Source: frontend/niuma-neon-pulse-prototype.html
 * ============================================================ */
"""
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(header.format(block_count=len(blocks)))
        f.write('\n')
        f.write(css)
    
    print(f"\n[DONE] Written to: {OUTPUT_FILE}")
    print(f"[NEXT] Add <link> to index.html to load this file AFTER other CSS files")


if __name__ == '__main__':
    main()
