import pandas as pd
import numpy as np
import re

print("Loading original Excel file...")
df = pd.read_excel('Prakalp_IOT_Sprint_Final_Batches.xlsx')

# The teams are grouped by "Batch NO". The Leader is the first row where Batch NO is not empty.
# We forward-fill the batch number so we know which team each row belongs to
df['Batch NO_Filled'] = df['Batch NO'].ffill()

# Drop duplicates to keep ONLY the first member (Leader) of every batch
leaders = df.drop_duplicates(subset=['Batch NO_Filled'], keep='first')

output_data = []
team_counter = 1

for index, row in leaders.iterrows():
    batch_str = str(row['Batch NO_Filled'])
    
    # Try to extract a clean Project ID from the weird batch string natively
    # e.g., 'PRAKALP/IOT-SPRINT/LIBRARY/001' -> '001'
    project_id = batch_str.split('/')[-1] if '/' in batch_str else f"PROJ-{team_counter}"
    
    # Clean the email properly
    leader_email = str(row['Mail Id']).strip()
    if leader_email == 'nan':
        leader_email = 'no-email-found@example.com'
        
    # Clean Team Name naturally
    leader_name = str(row['Name of The Student']).strip()
    team_name = leader_name.split()[0] + "'s Team" if leader_name != 'nan' else f"Team {team_counter}"

    output_data.append({
        'TeamID': team_counter,
        'ProjectID': project_id,
        'TeamName': team_name,
        'ProjectTitle': "Pending Assignment", # Ready for you to fill in or map
        'LeaderEmail': leader_email
    })
    team_counter += 1

output_df = pd.DataFrame(output_data)

# Export perfectly formatted to both XLSX and CSV for the Hackathon Admin panel
output_df.to_excel('Prakalp_Formatted_Registry.xlsx', index=False)
output_df.to_csv('data/sample_teams_registry.csv', index=False)

print(f"[SUCCESS] Converted {len(output_df)} teams!")
print("Saved to: Prakalp_Formatted_Registry.xlsx")
