from pypdf import PdfReader
import textwrap
import re

def word_wrap(text, width):
    """Wrap text to a given width."""
    return '\n'.join(textwrap.wrap(text, width=width))

def normalize_text(text):
    """Remove excessive whitespace and line breaks for reliable matching."""
    return re.sub(r'\s+', ' ', text.strip())

# Load PDF
reader = PdfReader("prompts/promt verdict eng (3).pdf")
pdf_text = [p.extract_text() for p in reader.pages if p.extract_text()]

# --- Part 1: Extract up until Part 2 marker ---
part2_marker = "#  PALEONTOLOGY  VISION  MASTER  PROMPT  —  PART  2"
combined_text_part1 = ""

for page_text in pdf_text:
    page_norm = normalize_text(page_text)
    if part2_marker.lower() in page_norm.lower():
        before_marker = re.split(re.escape(part2_marker), page_norm, flags=re.IGNORECASE)[0]
        combined_text_part1 += before_marker.strip()
        break
    else:
        combined_text_part1 += page_norm + " "

# --- Part 2: Extract Worked JSON Examples section ---
start_marker = "## WORKED JSON EXAMPLES"
stop_marker = "### Example 4: Shark Tooth (Megalodon)"
combined_text_part2 = ""
start_collecting = False

for page_text in pdf_text:
    page_norm = normalize_text(page_text)
    
    if start_collecting:
        if stop_marker.lower() in page_norm.lower():
            before_stop = re.split(re.escape(stop_marker), page_norm, flags=re.IGNORECASE)[0]
            combined_text_part2 += before_stop.strip()
            print("Found stop marker")
            break
        else:
            combined_text_part2 += page_norm + " "
    
    elif start_marker.lower() in page_norm.lower():
        start_collecting = True
        after_start = re.split(re.escape(start_marker), page_norm, flags=re.IGNORECASE)[1]
        combined_text_part2 += after_start.strip() + " "
        print("Found start marker")

# --- Combine both sections ---
final_prompt = combined_text_part1 + " " + combined_text_part2
final_prompt_wrapped = word_wrap(final_prompt, 100)

print("Extraction complete. Prompt length:", len(final_prompt_wrapped))
