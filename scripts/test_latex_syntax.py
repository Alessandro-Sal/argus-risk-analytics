import glob
import re

def test_latex_in_file(fpath):
    with open(fpath, 'r', encoding='utf-8') as f:
        text = f.read()

    errors = []
    
    # Remove code blocks
    text_no_code = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text_no_code = re.sub(r'`[^`\n]+`', '', text_no_code)

    # 1. Extract $$ ... $$ blocks
    double_blocks = re.findall(r'\$\$(.*?)\$\$', text_no_code, flags=re.DOTALL)
    
    # 2. Extract $ ... $ inline blocks
    # Be careful not to match $$
    single_blocks = re.findall(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', text_no_code)

    all_blocks = [("display", b) for b in double_blocks] + [("inline", b) for b in single_blocks]

    for btype, block in all_blocks:
        # Check matching curly braces { } (ignoring escaped \{ and \})
        clean = block.replace(r'\{', '').replace(r'\}', '')
        open_c = clean.count('{')
        close_c = clean.count('}')
        if open_c != close_c:
            errors.append(f"Unmatched braces in {btype} math: open={open_c}, close={close_c}\nContent: {block.strip()[:100]}...")

        # Check matching \left and \right
        lefts = len(re.findall(r'\\left(?![a-zA-Z])', block))
        rights = len(re.findall(r'\\right(?![a-zA-Z])', block))
        if lefts != rights:
            errors.append(f"Unmatched \\left/\\right in {btype} math: \\left={lefts}, \\right={rights}\nContent: {block.strip()[:100]}...")

        # Check matching \begin{env} and \end{env}
        begins = re.findall(r'\\begin\{([a-zA-Z*]+)\}', block)
        ends = re.findall(r'\\end\{([a-zA-Z*]+)\}', block)
        if begins != ends:
            errors.append(f"Mismatched begin/end environments: {begins} vs {ends}\nContent: {block.strip()[:100]}...")

    return errors

for fpath in sorted(glob.glob('docs/**/*.md', recursive=True)) + ['README.md']:
    errs = test_latex_in_file(fpath)
    if errs:
        print(f"=== ERRORS IN {fpath} ===")
        for e in errs:
            print(f"  * {e}")
print("LaTeX syntax validation finished.")
