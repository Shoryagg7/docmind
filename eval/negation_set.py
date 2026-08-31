NEGATION_PAIRS = [
    {
        "label": "drug approval",
        "statement": "The drug is approved for adult use.",
        "negation": "The drug is not approved for adult use.",
    },
    {
        "label": "refund eligibility (from sample2.pdf)",
        "statement": "Enterprise customers are eligible for the standard 14-day refund window.",
        "negation": "Enterprise customers are not eligible for the standard 14-day refund window.",
    },
    {
        "label": "support hours",
        "statement": "Starter tier customers receive 24/7 phone support.",
        "negation": "Starter tier customers do not receive 24/7 phone support.",
    },
    {
        "label": "encryption",
        "statement": "All data is encrypted at rest.",
        "negation": "Data is not encrypted at rest.",
    },
    {
        "label": "employment",
        "statement": "Maya Chen currently works at Northwind Analytics.",
        "negation": "Maya Chen no longer works at Northwind Analytics.",
    },
    {
        "label": "certification",
        "statement": "Nimbus Cloud Storage is SOC 2 Type II certified.",
        "negation": "Nimbus Cloud Storage is not SOC 2 Type II certified.",
    },
]

# Control pairs: genuinely different statements on the same topic. These are the
# baseline a negation pair should score BELOW, if embeddings understood negation.
CONTROL_PAIRS = [
    {
        "label": "different fact, same doc",
        "statement": "The Starter tier costs 5 dollars per month.",
        "other": "The Pro tier costs 15 dollars per month.",
    },
    {
        "label": "different fact, same person",
        "statement": "Maya Chen works in Toronto.",
        "other": "Maya Chen graduated from the University of Waterloo.",
    },
    {
        "label": "unrelated topics",
        "statement": "Maya Chen plays the violin.",
        "other": "Deleted files are retained for 30 days.",
    },
]
