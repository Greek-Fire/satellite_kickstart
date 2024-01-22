import requests
import yaml
import argparse
import csv
from urllib3.exceptions import InsecureRequestWarning

class APIClient:
    def __init__(self, config_path):
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            self.token       = config['token']
            self.base_url    = config['base_url']
            self.verify_ssl  = config['verify_ssl']
            self.report_path = config.get('report_path', '') 

        except FileNotFoundError:
            print(f"Error: The file '{config_path}' was not found.")
            exit(1)  # Exit the program
        except yaml.YAMLError as e:
            print(f"Error parsing YAML in '{config_path}': {e}")
            exit(1)
        except KeyError as e:
            print(f"Error: The key '{e}' is missing in the configuration file.")
            exit(1)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            exit(1)

    def get_data(self):
        url = f'{self.base_url}/api/v2/jobs?page_size=9999'
        headers = {'Authorization': f'Bearer {self.token}'}
        response = requests.get(url, headers=headers, verify=self.verify_ssl)
        return response.json()

class ReportGenerator:
    def __init__(self, data, report_path):
        self.data = data
        self.report_path = report_path

    def generate_report(self, file_name='report.csv'):
        # Use self.report_path to determine the full path
        full_file_path = f'{self.report_path}/{file_name}' if self.report_path else file_name

        headers = ['Name', 'job_type', 'failures', 'success', 'total']
        with open(full_file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)

            for job in self.data['results']:
                if job['limit'] == "":
                    total = job['summary_fields']['inventory']['total_hosts']
                else:
                    total = len(job['limit'].split(','))

                row = [job['name'], job['job_type'], total]
                writer.writerow(row)

        print(f"Report generated: {full_file_path}")

class CLI:
    def __init__(self):
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        parser = argparse.ArgumentParser(description="CLI tool to fetch data from API and generate reports")
        parser.add_argument("--config", type=str, default='/home/fake_user/.config.yml', help="Path to the config YAML file")

        args = parser.parse_args()
        self.config_path = args.config
        self.client = APIClient(self.config_path)

    def run(self):
        data = self.client.get_data()
        report_generator = ReportGenerator(data, self.client.report_path)
        report_generator.generate_report()

def main():
    cli = CLI()
    cli.run()

if __name__ == "__main__":
    main()