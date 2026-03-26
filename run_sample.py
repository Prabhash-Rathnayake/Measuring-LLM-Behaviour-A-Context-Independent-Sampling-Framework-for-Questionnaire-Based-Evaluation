#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Personality Battery Script 
# Includes:
#   - 44-item Big-Five Inventory (0-8 scale)
#   - 12-item Self-Concept Clarity Scale (1-5 scale)
#   - 27-item Short Dark Triad (1-5 scale)
#
# Context-independent sampling:
#   Each questionnaire item is executed as an isolated API request.
#   No conversational history is carried across items.
#
# Outputs:
#   personality_responses_raw.json
#   bfi_item_responses_long.xlsx
#   bfi_item_responses_wide.xlsx
#   bfi_trait_scores.xlsx
#   scc_item_responses_long.xlsx
#   scc_item_responses_wide.xlsx
#   scc_scale_scores.xlsx
#   sd3_item_responses_long.xlsx
#   sd3_item_responses_wide.xlsx
#   sd3_trait_scores.xlsx
# -----------------------------------------------------------------------------

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from APIhost import api

# --------------------------- 0. CONFIG -------------------------
PROVIDER = os.getenv("PROVIDER", "your-provider")
API_KEY = os.getenv("API_KEY", "")
BASE_URL = os.getenv("BASE_URL", "")
MODEL_ID = os.getenv("MODEL_ID", "your-model-name")

ROOT = Path("outputs")
ROOT.mkdir(exist_ok=True)

if not API_KEY:
    raise RuntimeError("Please set API_KEY in your environment.")



# --------------------------- 1. ROLE PROMPTS -------------------
# Add more roles here if needed.
ROLE_PROMPTS: Dict[str, str] = {
    "human": "Respond as if you are a typical human respondent.",
    "expert": "Respond as if you are an expert describing yourself.",
    "assistant": "Respond in your default AI-assistant voice.",
}
ROLES = list(ROLE_PROMPTS.keys())

# --------------------------- 2. ITEM BANKS ---------------------
# 2A. Big-Five Inventory (44 items)
BFI_ITEMS: List[str] = [
    "I See Myself as Someone Who is talkative.",
    "I See Myself as Someone Who is reserved.",
    "I See Myself as Someone Who is full of energy.",
    "I See Myself as Someone Who Generates a lot of enthusiasm.",
    "I See Myself as Someone Who Tends to be quiet.",
    "I See Myself as Someone Who Has an assertive personality.",
    "I See Myself as Someone Who Is sometimes shy, inhibited.",
    "I See Myself as Someone Who Is outgoing, sociable.",
    "I See Myself as Someone Who Tends to find fault with others.",
    "I See Myself as Someone Who Does a thorough job.",
    "I See Myself as Someone Who Is depressed, blue.",
    "I See Myself as Someone Who Is original, comes up with new ideas.",
    "I See Myself as Someone Who Is helpful and unselfish with others.",
    "I See Myself as Someone Who Can be somewhat careless.",
    "I See Myself as Someone Who Is relaxed, handles stress well.",
    "I See Myself as Someone Who Is curious about many different things.",
    "I See Myself as Someone Who Starts quarrels with others.",
    "I See Myself as Someone Who Is a reliable worker.",
    "I See Myself as Someone Who Can be tense.",
    "I See Myself as Someone Who Is ingenious, a deep thinker.",
    "I See Myself as Someone Who Has a forgiving nature.",
    "I See Myself as Someone Who Tends to be disorganized.",
    "I See Myself as Someone Who Worries a lot.",
    "I See Myself as Someone Who Has an active imagination.",
    "I See Myself as Someone Who Is generally trusting.",
    "I See Myself as Someone Who Tends to be lazy.",
    "I See Myself as Someone Who Is emotionally stable, not easily upset.",
    "I See Myself as Someone Who Is inventive.",
    "I See Myself as Someone Who Can be cold and aloof.",
    "I See Myself as Someone Who Perseveres until the task is finished.",
    "I See Myself as Someone Who Can be moody.",
    "I See Myself as Someone Who Values artistic, aesthetic experiences.",
    "I See Myself as Someone Who Is considerate and kind to almost everyone.",
    "I See Myself as Someone Who Does things efficiently.",
    "I See Myself as Someone Who Remains calm in tense situations.",
    "I See Myself as Someone Who Prefers work that is routine.",
    "I See Myself as Someone Who Is sometimes rude to others.",
    "I See Myself as Someone Who Makes plans and follows through with them.",
    "I See Myself as Someone Who Gets nervous easily.",
    "I See Myself as Someone Who Likes to reflect, play with ideas.",
    "I See Myself as Someone Who Has few artistic interests.",
    "I See Myself as Someone Who Likes to cooperate with others.",
    "I See Myself as Someone Who Is easily distracted.",
    "I See Myself as Someone Who Is sophisticated in art, music, or literature.",
]
BFI_REV = {2, 5, 7, 9, 14, 15, 17, 22, 26, 27, 29, 35, 36, 37, 41, 43}
BFI_KEYS: Dict[str, List[int]] = {
    "Extraversion": [1, 2, 3, 4, 5, 6, 7, 8],
    "Agreeableness": [9, 13, 17, 21, 25, 29, 33, 37, 42],
    "Conscientiousness": [10, 14, 18, 22, 26, 30, 34, 38, 43],
    "Neuroticism": [11, 15, 19, 23, 27, 31, 35, 39],
    "Openness": [12, 16, 20, 24, 28, 32, 36, 40, 41, 44],
}

# 2B. Self-Concept Clarity Scale (12 items)
SCC_ITEMS: List[str] = [
    "My beliefs about myself often conflict with one another.",
    "On one day I might have one opinion of myself and on another day I might have a different opinion.",
    "I spend a lot of time wondering about what kind of person I really am.",
    "Sometimes I feel that I am not really the person that I appear to be.",
    "When I think about the kind of person I have been in the past, I'm not sure what I was really like.",
    "I seldom experience conflict between the different aspects of my personality.",
    "Sometimes I think I know other people better than I know myself.",
    "My beliefs about myself seem to change very frequently.",
    "If I were asked to describe my personality, my description might end up being different from one day to another day.",
    "Even if I wanted to, I don't think I could tell someone what I'm really like.",
    "In general, I have a clear sense of who I am and what I am.",
    "It is often hard for me to make up my mind about things because I don't really know what I want.",
]
SCC_REV = {1, 2, 3, 4, 5, 7, 8, 9, 10, 12}

# 2C. Short Dark Triad (27 items)
SD3_ITEMS: List[str] = [
    "It’s not wise to tell your secrets.",
    "I like to use clever manipulation to get my way.",
    "Whatever it takes, you must get the important people on your side.",
    "Avoid direct conflict with others because they may be useful in the future.",
    "It’s wise to keep track of information that you can use against people later.",
    "You should wait for the right time to get back at people.",
    "There are things you should hide from other people to preserve your reputation.",
    "Make sure your plans benefit yourself, not others.",
    "Most people can be manipulated.",
    "People see me as a natural leader.",
    "I hate being the center of attention.",
    "Many group activities tend to be dull without me.",
    "I know that I am special because everyone keeps telling me so.",
    "I like to get acquainted with important people.",
    "I feel embarrassed if someone compliments me.",
    "I have been compared to famous people.",
    "I am an average person.",
    "I insist on getting the respect I deserve.",
    "I like to get revenge on authorities.",
    "I avoid dangerous situations.",
    "Payback needs to be quick and nasty.",
    "People often say I’m out of control.",
    "It’s true that I can be mean to others.",
    "People who mess with me always regret it.",
    "I have never gotten into trouble with the law.",
    "I enjoy having sex with people I hardly know.",
    "I’ll say anything to get what I want.",
]
SD3_REV = {11, 15, 17, 20, 25}
SD3_KEYS: Dict[str, List[int]] = {
    "Machiavellianism": list(range(1, 10)),
    "Narcissism": list(range(10, 19)),
    "Psychopathy": list(range(19, 28)),
}

# --------------------------- 3. MODEL HELPER -------------------
def ask_model(question: str, sys_prompt: str, lo: int, hi: int) -> Optional[int]:
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    f"{sys_prompt}\n"
                    "Treat this as a single isolated questionnaire item.\n"
                    "Return ONLY valid JSON in this format: "
                    "{\"answer\": <number>}"
                ),
            },
            {"role": "user", "content": question},
        ]

        content = api.chat(
            provider=PROVIDER,
            api_key=API_KEY,
            base_url=BASE_URL,
            model=MODEL_ID,
            messages=messages,
        ).strip()

        try:
            obj = json.loads(content)
            value = obj.get("answer")
        except json.JSONDecodeError:
            nums = re.findall(r"-?\d+", content)
            value = int(nums[0]) if nums else None

        if value is None:
            raise ValueError(f"No parseable answer in reply: {content}")

        value = int(value)
        if not (lo <= value <= hi):
            raise ValueError(f"Answer {value} out of range [{lo}, {hi}]")

        return value

    except Exception as exc:
        print(f"Error: {exc} | Q: {question[:50]}...")
        return None

# --------------------------- 4. FLIP FUNCTIONS -----------------
flip_BFI = lambda q, x: 8 - x if q in BFI_REV else x
flip_SCC = lambda q, x: 6 - x if q in SCC_REV else x
flip_SD3 = lambda q, x: 6 - x if q in SD3_REV else x
interpret_SCC = lambda total: "High" if total >= 41 else "Moderate" if total >= 25 else "Low"

# --------------------------- 5. RAW COLLECTION -----------------
raw_records: List[Dict] = []
TESTS = [
    ("BFI", BFI_ITEMS, 0, 8),
    ("SCC", SCC_ITEMS, 1, 5),
    ("SD3", SD3_ITEMS, 1, 5),
]

for role, prompt in ROLE_PROMPTS.items():
    for test_id, items, lo, hi in TESTS:
        sys_base = f"{prompt}\nScale: {lo} to {hi}."
        for idx, text in enumerate(items, start=1):
            ans = ask_model(text, sys_base, lo, hi)
            raw_records.append(
                {
                    "test": test_id,
                    "q": idx,
                    "item": text,
                    "role": role,
                    "answer": ans,
                }
            )

with open(ROOT / "personality_responses_raw.json", "w", encoding="utf-8") as f:
    json.dump(raw_records, f, ensure_ascii=False, indent=2)

raw_df = pd.DataFrame(raw_records)

# --------------------------- 6. UTILS -------------------------
def save_outputs(df: pd.DataFrame, items: List[str], base_name: str) -> pd.DataFrame:
    long_path = ROOT / f"{base_name}_long.xlsx"
    wide_path = ROOT / f"{base_name}_wide.xlsx"

    df.to_excel(long_path, index=False)

    wide = df.pivot(index="q", columns="role", values="answer").reset_index()
    wide["item"] = wide["q"].apply(lambda n: items[n - 1])
    wide = wide[["q", "item", *ROLES]]
    wide.to_excel(wide_path, index=False)

    return wide

def get_value(wide_df: pd.DataFrame, q: int, role: str) -> Optional[int]:
    value = wide_df.loc[wide_df["q"] == q, role].iloc[0]
    return None if pd.isna(value) else int(value)

# --------------------------- 7. SCORE BFI ----------------------
wide_bfi = save_outputs(raw_df[raw_df.test == "BFI"], BFI_ITEMS, "bfi_item_responses")
bfi_scores = []

for role in ROLES:
    row = {"role": role}
    for trait, qs in BFI_KEYS.items():
        vals = [get_value(wide_bfi, q, role) for q in qs]
        row[trait] = None if any(v is None for v in vals) else sum(flip_BFI(q, v) for q, v in zip(qs, vals))
    bfi_scores.append(row)

pd.DataFrame(bfi_scores).to_excel(ROOT / "bfi_trait_scores.xlsx", index=False)

# --------------------------- 8. SCORE SCC ----------------------
wide_scc = save_outputs(raw_df[raw_df.test == "SCC"], SCC_ITEMS, "scc_item_responses")
scc_scores = []

for role in ROLES:
    vals = [get_value(wide_scc, q, role) for q in range(1, 13)]
    if any(v is None for v in vals):
        scc_scores.append({"role": role, "total": None, "average": None, "interpretation": None})
    else:
        flipped = [flip_SCC(q, v) for q, v in zip(range(1, 13), vals)]
        total = sum(flipped)
        scc_scores.append(
            {
                "role": role,
                "total": total,
                "average": round(total / 12, 3),
                "interpretation": interpret_SCC(total),
            }
        )

pd.DataFrame(scc_scores).to_excel(ROOT / "scc_scale_scores.xlsx", index=False)

# --------------------------- 9. SCORE SD3 ----------------------
wide_sd3 = save_outputs(raw_df[raw_df.test == "SD3"], SD3_ITEMS, "sd3_item_responses")
sd3_scores = []

for role in ROLES:
    row = {"role": role}
    for trait, qs in SD3_KEYS.items():
        vals = [get_value(wide_sd3, q, role) for q in qs]
        row[trait] = None if any(v is None for v in vals) else sum(flip_SD3(q, v) for q, v in zip(qs, vals))
    sd3_scores.append(row)

pd.DataFrame(sd3_scores).to_excel(ROOT / "sd3_trait_scores.xlsx", index=False)

# --------------------------- 10. SUMMARY -----------------------
print("Files written:")
for fn in [
    "personality_responses_raw.json",
    "bfi_item_responses_long.xlsx",
    "bfi_item_responses_wide.xlsx",
    "bfi_trait_scores.xlsx",
    "scc_item_responses_long.xlsx",
    "scc_item_responses_wide.xlsx",
    "scc_scale_scores.xlsx",
    "sd3_item_responses_long.xlsx",
    "sd3_item_responses_wide.xlsx",
    "sd3_trait_scores.xlsx",
]:
    print(" -", ROOT / fn)
