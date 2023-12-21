#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
import os
import hashlib

def generate_pulp_manifest(directory, ignore_file='PULP_MANIFEST'):
    manifest = {}
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename == ignore_file:
                continue  # Skip the PULP_MANIFEST file
            # Construct the relative file path from the directory
            file_path = os.path.join(root, filename)
            relative_file_path = os.path.relpath(file_path, directory)
            if relative_file_path in manifest:
                continue  # Skip if already processed this file path
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(8192)
                    if not data:
                        break
                    hasher.update(data)
            file_size = os.path.getsize(file_path)
            # Use the relative path for the file entry
            manifest[relative_file_path] = f"{relative_file_path},{hasher.hexdigest()},{file_size}"
    manifest_content = "\n".join(manifest.values())
    return manifest_content

def main():
    module = AnsibleModule(
        argument_spec=dict(
            src=dict(type='str', required=True),
            path=dict(type='str', required=True),
            force=dict(type='bool', required=False, default=False)
        )
    )
    
    directory = module.params['src']
    manifest_file = module.params['path']
    force = module.params['force']

    if not os.path.isdir(directory):
        module.fail_json(msg=f"The directory {directory} does not exist")

    if os.path.isfile(manifest_file) and not force:
        module.exit_json(changed=False, message=f"PULP_MANIFEST already exists at {manifest_file}. No changes made.")

    try:
        manifest_content = generate_pulp_manifest(directory)
        with open(manifest_file, 'w') as f:
            f.write(manifest_content)
        module.exit_json(changed=True, message=f"PULP_MANIFEST has been generated at {manifest_file}")
    except Exception as e:
        module.fail_json(msg=str(e))

if __name__ == '__main__':
    main()
