"""Generate diverse, synthetic Week 7 intent-classification candidates.

Run from the IDX Exchange NLP repository root:
    python scripts/generate_week7_candidates.py

Candidates are NOT verified user queries. Review manually before training.
"""

from pathlib import Path
import pandas as pd


BROWSING = """
Browse small single-story houses in Carlsbad
What homes are available with a detached guest suite?
Show loft-style condos with high ceilings
Find houses with a covered backyard patio
Browse listings in neighborhoods with tree-lined streets
Show homes with a separate dining room
Find duplex listings in North County
Are there ranch-style homes with large lots?
Show me waterfront condos with balconies
Browse homes that have a dedicated workshop
Find houses with an upstairs laundry room
Show properties featuring a three-car garage
Browse newly listed cottages near La Mesa
"""

RESEARCHING = """
How have median home prices changed in Irvine over five years?
Compare price per square foot for condos and townhouses in San Diego
Which neighborhoods offer the best value for a first-time buyer?
How much do homes typically sell above asking price in Carlsbad?
What is the average time on market for houses in La Jolla?
Compare the long-term cost of buying a condo versus a detached house
How do property prices differ between coastal and inland neighborhoods?
What price trends should I expect in North County next year?
Which zip codes have seen the largest home price declines?
How do recently sold prices compare with current asking prices?
What are the differences in school ratings between Carmel Valley and Poway?
Compare neighborhood walkability in Encinitas and Solana Beach
Which San Diego areas have shorter average commutes to downtown?
How do noise levels compare near major freeways?
What are the pros and cons of living near an airport?
Which neighborhoods have reliable access to public transit?
How do local crime statistics vary between these communities?
Compare grocery and park access in Mira Mesa and Scripps Ranch
What should I know about future development near this neighborhood?
Which areas offer more public green space per resident?
How do rental yields compare between duplexes and single-family houses?
What vacancy rates are typical for investment condos in San Diego?
Compare cap rates for properties in Oceanside versus Vista
Which expenses should I include in a rental cash-flow calculation?
How much does property management typically reduce net rental income?
What are the risks of buying a short-term rental property?
How do maintenance costs affect returns on older rental homes?
Compare appreciation and rental income potential for two neighborhoods
Is a duplex generally easier to rent than a large luxury house?
How should I estimate return on investment for a fixer-upper?
How do annual property taxes differ between these two houses?
What is included in the monthly HOA fee for this condo complex?
Compare total monthly ownership costs with and without an HOA
How much should I budget for homeowners insurance near the coast?
What special assessments have been charged in this HOA?
How do mortgage points change the long-term cost of a loan?
What would a higher interest rate do to my monthly payment?
Compare the costs of a 15-year and 30-year mortgage
Are there differences in insurance costs between condos and houses?
How much should I reserve annually for home maintenance?
What are the tradeoffs between buying new construction and an older home?
Compare townhouse ownership responsibilities with condo ownership
Which home features contribute most to resale value?
How long do tile roofs typically last compared with asphalt roofs?
What are the benefits and drawbacks of buying a home with solar panels?
How does lot size affect a property's long-term value?
What should I consider when comparing two different floor plans?
Do homes with an additional bathroom command higher resale prices?
Which renovations tend to have the strongest return at resale?
How should I compare homes with different amounts of usable space?
Which neighborhoods face greater wildfire exposure?
How can I compare flood risk for homes near the coast?
What should buyers research about earthquake retrofit requirements?
How do summer temperatures differ across inland San Diego areas?
Which communities have more restrictive short-term rental rules?
What questions should I ask about an older home's plumbing system?
How can I assess traffic congestion around two school districts?
What should I check in a neighborhood's future zoning plans?
How do utility bills compare for similar houses with different insulation?
What should I research about water restrictions before buying?
Is this market currently favoring buyers or sellers?
What does a rising inventory level usually mean for negotiations?
How can I evaluate whether a listing price is reasonable?
Compare recent sales concessions across neighboring zip codes
What factors make a home more difficult to resell?
How do seasonality and interest rates affect local housing demand?
What information belongs in a comparative market analysis?
"""

HIGH_INTENT = """
Can I schedule a private showing of this house tomorrow?
Book a tour of the listing on Oak Street for Saturday morning
I'd like to see this condo in person after work today
Is there an agent who can show me this property this afternoon?
Please arrange back-to-back tours of these two houses on Sunday
Can someone confirm a viewing appointment for Friday at 3 pm?
I'd like to tour the newly listed townhouse before the weekend
Help me book an in-person visit to this home as soon as possible
Can we visit the property tomorrow before submitting an offer?
Please reserve the earliest available showing slot for this listing
Connect me with the listing agent about buying this condo
Can the seller's agent call me today about this property?
I want to ask the agent whether the house is still available
Please send my contact details to the agent for this listing
Can you arrange a call with the seller's representative tomorrow?
I'd like an agent to walk me through the next steps this week
Please have someone contact me to discuss a specific property
Can I speak to the listing agent before tonight's deadline?
I need an agent to help coordinate a visit this weekend
Who can I contact right now to discuss this home?
I am ready to submit an offer on this house today
How do I send a written offer for this listed property?
Please help me prepare a purchase offer before the deadline
Can I put in an offer at the asking price this afternoon?
I want to make a counteroffer to the seller by tonight
Who should receive my signed offer documents?
Can we submit an offer contingent on inspection tomorrow?
I have chosen this property and want to start the offer process
Can my agent send an updated offer before 5 pm?
Please confirm whether the seller is accepting offers this week
I need a home I can move into before the end of this month
Can I close on this property within the next 30 days?
I'm relocating next week and need to arrange a viewing now
Is this vacant home available for immediate occupancy?
I want to finalize a purchase before my lease expires next month
Can the seller accommodate a closing date of December 10?
I need to move quickly; when can we inspect this house?
Can we begin the purchase paperwork this week?
I'm ready to proceed if this home can close within six weeks
Please help me confirm a move-in date with the seller today
Can we schedule the home inspection for next Tuesday?
I want to order an inspection before my contingency deadline
Please arrange an appraisal for the property we're buying
Can the seller send the disclosure package today?
I need to review the HOA documents before signing tomorrow
Please confirm the inspection appointment with the agent
Can you connect me with an inspector this week?
We are under contract; how do we schedule the final walkthrough?
I need to send the earnest-money deposit instructions today
Can I get the seller's repair response before the deadline?
I have preapproval and want to tour this house today
Can I send my lender's preapproval letter with an offer tomorrow?
I want to start the mortgage application for this specific home
Please connect my loan officer with the listing agent this week
Can you request the estimated closing costs for this purchase?
My financing is ready; when can we schedule a showing?
I need a lender confirmation before submitting the offer tonight
Can we lock the mortgage rate for this purchase today?
I have proof of funds and would like to make an offer this week
Please ask the agent what financing documents are needed now
Can you register me for the open house this Saturday?
Is there a tour slot available at the property this weekend?
I'd like to attend the open house tomorrow at noon
Please set up a video walkthrough with the agent today
Can you book a second viewing with my family on Sunday?
I want to bring my contractor for a visit later this week
Could you arrange an evening appointment to see the condo?
I need to view the home before the offer window closes
Please schedule a same-day virtual tour of this listing
Can you confirm the address and check-in details for tomorrow's open house?
"""


def lines(block: str) -> list[str]:
    return [line.strip() for line in block.strip().splitlines() if line.strip()]


def main() -> None:
    existing_path = Path("data/annotations/week7_intent_queries.csv")
    output_path = Path("data/annotations/week7_candidate_queries.csv")
    if not existing_path.exists():
        raise FileNotFoundError(f"Run from repository root; missing {existing_path}")
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing {output_path}")

    existing = pd.read_csv(existing_path)
    existing_keys = set(existing["query"].dropna().astype(str).str.strip().str.casefold())

    sections = {
        "browsing": lines(BROWSING),
        "researching": lines(RESEARCHING),
        "high_intent_inquiry": lines(HIGH_INTENT),
    }
    expected = {"browsing": 13, "researching": 67, "high_intent_inquiry": 70}
    counts = {label: len(queries) for label, queries in sections.items()}
    if counts != expected:
        raise ValueError(f"Unexpected candidate counts: {counts}; expected {expected}")

    rows = [
        {"query": query, "intent": intent, "source": "synthetic", "review_status": "pending"}
        for intent, queries in sections.items()
        for query in queries
    ]
    df = pd.DataFrame(rows)
    normalized = df["query"].str.strip().str.casefold()
    if normalized.duplicated().any():
        raise ValueError("Duplicate candidates: " + str(df.loc[normalized.duplicated(), "query"].tolist()))
    overlap = normalized[normalized.isin(existing_keys)]
    if len(overlap):
        raise ValueError(f"Candidates already present in existing data: {overlap.tolist()}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Created: {output_path}")
    print(f"Candidate rows: {len(df)}")
    print(df["intent"].value_counts().to_string())
    print("Source: synthetic (not real user queries)")
    print("Review status: pending (not yet approved for training)")


if __name__ == "__main__":
    main()
