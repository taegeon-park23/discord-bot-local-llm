
import requests

BASE_URL = "http://localhost:8000"

def check_counts():
    response = requests.get(f"{BASE_URL}/api/documents?limit=1000")
    if response.status_code == 200:
        docs = response.json()
        total = len(docs)
        cats = {}
        for d in docs:
            c = d.get('category', 'Unknown')
            cats[c] = cats.get(c, 0) + 1
        
        print(f"Total documents: {total}")
        print("Category Distribution:")
        for c, count in sorted(cats.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {c}: {count}")
    else:
        print(f"Failed to fetch: {response.status_code}")

if __name__ == "__main__":
    check_counts()
