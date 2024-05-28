import pandas as pd
from datetime import datetime, timedelta
import random

# Seed for reproducibility
random.seed(42)

# Generate sample data
data = {
    "Employee ID": range(1, 101),  # 100 employees
    "Name": [f"Employee {i}" for i in range(1, 101)],
    "Join Date": [(datetime.now() - timedelta(days=random.randint(1, 365 * 5))).strftime('%Y-%m-%d') for _ in range(100)],
    "Salary": [random.randint(50000, 120000) for _ in range(100)],
    "Department": [random.choice(['HR', 'Marketing', 'Finance', 'IT', 'Sales']) for _ in range(100)]
}

# Create a DataFrame
df = pd.DataFrame(data)

# Save to CSV
csv_file_path = 'sample_employees.csv'
df.to_csv(csv_file_path, index=False)

print(f"Sample data saved to {csv_file_path}")
