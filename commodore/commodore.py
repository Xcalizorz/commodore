import click, json, os
from kapitan.resources import inventory_reclass

from .git import clone_repository, checkout_version
from .helpers import clean, api_request, kapitan_compile, ApiError
from .postprocess import postprocess_components

def fetch_cluster_spec(cfg, customer, cluster):
    return api_request(cfg.api_url, 'inventory', customer, cluster)

def fetch_config(cfg, response):
    config = response['global']['config']
    print(f"Updating global config...")
    clone_repository(f"{cfg.global_git_base}/{config}.git", f"inventory/classes/global")

def fetch_component(cfg, component):
    repository_url = f"{cfg.global_git_base}/commodore-components/{component}.git"
    target_directory = f"dependencies/{component}"
    repo = clone_repository(repository_url, target_directory)
    cfg.register_component(component, repo)
    os.symlink(os.path.abspath(f"{target_directory}/class/{component}.yml"), f"inventory/classes/components/{component}.yml")

def fetch_components(cfg, response):
    components = response['global']['components']
    os.makedirs('inventory/classes/components', exist_ok=True)
    print("Updating components...")
    for c in components:
        print(f" > {c}...")
        fetch_component(cfg, c)

def set_component_version(cfg, component, version):
    print(f" > {component}: {version}")
    checkout_version(cfg.get_component_repo(component), version)

def set_component_versions(cfg, versions):
    print("Setting component versions...")
    for cn, c in versions.items():
        set_component_version(cfg, cn, c['version'])

def fetch_target(cfg, customer, cluster):
    return api_request(cfg.api_url, 'targets', customer, cluster)

def update_target(cfg, customer, cluster):
    print("Updating Kapitan target...")
    try:
        target = fetch_target(cfg, customer, cluster)
    except ApiError as e:
        raise click.ClickException(f"While fetching target: {e}") from e

    target_name = target['target']
    os.makedirs('inventory/targets', exist_ok=True)
    with open(f"inventory/targets/{target_name}.yml", 'w') as tgt:
        json.dump(target['contents'], tgt)

    return target_name

def fetch_customer_config(cfg, repo, customer):
    if repo is None:
        repo = f"{cfg.customer_git_base}/{customer}.git"
    print("Updating customer config...")
    clone_repository(repo, f"inventory/classes/{customer}")

def fetch_jsonnet_libs(cfg, response):
    print("Updating Jsonnet libraries...")
    os.makedirs('dependencies/libs', exist_ok=True)
    os.makedirs('dependencies/lib', exist_ok=True)
    libs = response['global']['jsonnet_libs']
    for lib in libs:
        libname = lib['name']
        filestext = ' '.join([ f['targetfile'] for f in lib['files'] ])
        print(f" > {libname}: {filestext}")
        repo = clone_repository(lib['repository'], f"dependencies/libs/{libname}")
        for file in lib['files']:
            os.symlink(os.path.abspath(f"{repo.working_tree_dir}/{file['libfile']}"),
                    f"dependencies/lib/{file['targetfile']}")

def compile(config, customer, cluster):
    clean()

    try:
        inv = fetch_cluster_spec(config, customer, cluster)
    except ApiError as e:
        raise click.ClickException(f"While fetching cluster specification: {e}") from e

    # Fetch all Git repos
    try:
        fetch_config(config, inv)
        fetch_components(config, inv)
        fetch_customer_config(config, inv['cluster'].get('override', None), customer)
        fetch_jsonnet_libs(config, inv)
    except Exception as e:
        raise click.ClickException(f"While cloning git repositories: {e}") from e

    target_name = update_target(config, customer, cluster)

    # Compile kapitan inventory to extract component versions. Component
    # versions are assumed to be defined in the inventory key
    # 'parameters.component_versions'
    kapitan_inventory = inventory_reclass('inventory')['nodes'][target_name]
    versions = kapitan_inventory['parameters']['component_versions']
    set_component_versions(config, versions)

    p = kapitan_compile(config.get_components())
    if p.returncode != 0:
        raise click.ClickException(f"Catalog compilation failed")

    postprocess_components(kapitan_inventory, target_name, config.get_components())