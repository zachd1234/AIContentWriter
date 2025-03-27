import os
import nest_asyncio
from api.openDeepResearcherAPI import OpenDeepResearcherAPI

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Initialize the researcher (using environment variables)
researcher = OpenDeepResearcherAPI()

# Run a simple research query
query = "How long is a Phase I ESA valid during property acquisition?"
max_iterations = 3  # Start with a small number for testing

# Run the research
report = researcher.run_research(query, max_iterations)

# Print the final report
print("\n\n=== FINAL RESEARCH REPORT ===\n\n")
print(report)