import subprocess as sp
import re
import os
from datetime import datetime

DEFAULT_CONFIG = 'debug'
DEFAULT_MAKE_OPERATION = ''

DEFAULT_LOG_FILE_PATH = r"C: \Users\yatesau\Documents\_Logs\project_builder"
DEFAULT_WORKSPACE_PATH = r"C:\Users\yatesau\Documents\momentics_workspace"
DEFAULT_VARIANT_DIRECTORY = "__VariantConfig__"
DEFAULT_BUILD_SCRIPT = ".build_order.txt"


def main():
    """Builds projects based on the .build_order.txt file.

    Reads in the .build_order.txt file to determine make operations and
    configuration settings for building the projects listed. By default,
    every vairiant inside the project's variant.mk file is built

    """
    build_script_name = DEFAULT_BUILD_SCRIPT
    workspace_path = DEFAULT_WORKSPACE_PATH
    variant_directory = DEFAULT_VARIANT_DIRECTORY
    master_variant_file = "variant.mk"

    build_script_path = os.path.join(workspace_path, build_script_name)
    build_operations = parseBuildOrders(build_script_path)

    variant_path = os.path.join(
        workspace_path, variant_directory, master_variant_file)
    variant_files = readBuildVariants(variant_path)

    for variant_file in variant_files:
        variant_path = os.path.join(
            workspace_path, variant_directory, variant_file)
        makeVariant(workspace_path, variant_path, build_operations)


def parseBuildOrders(build_script_path):
    """Reads .build_order.txt and returns a list of the make operations.

    Args:
        build_script_path (string): Path to the .build_order.txt file.

    Returns:
        dict: Returns a dictionary object containing the build instructions for
            each project.

    """
    with open(build_script_path) as script:
        build_script = script.readlines()
    build_script = [x.strip() for x in build_script]

    build_operations = {}

    config = DEFAULT_CONFIG
    make_operation = DEFAULT_MAKE_OPERATION

    op_offset = 0

    for line in build_script:
        if line is '':
            continue
        elif line.startswith('config'):
            config = line[7:]
        elif line.startswith('operation'):
            make_operation = line[10:]
        elif line[0].isdigit():
            op = int(line[0]) + op_offset
            path = line[2:]
            op_entry = build_operations.get(op, {})
            dirs = set()
            if op_entry.get('config', config) is not config:
                print("Warning: Cannot change configuration in the same",
                      "operation group. Creating a new operation group.")
                op += 1
                op_offset += 1
                op_entry = op_entry.copy()
            elif op_entry.get('operation',
                              make_operation) is not make_operation:
                print("Warning: Cannot change make operation in the same",
                      "operation group. Creating a new operation group.")
                op += 1
                op_offset += 1
                op_entry = op_entry.copy()
            else:
                dirs = op_entry.get('dirs', dirs)
            dirs.add(path)
            op_entry['config'] = config
            op_entry['operation'] = make_operation
            op_entry['dirs'] = dirs
            build_operations[op] = op_entry

    return build_operations


def readBuildVariants(file_path):
    """Reads variants file and returns a list of the variants to build.

    Args:
        file_path (string): Path to the variants file.

    Returns:
        list: Returns a list containing each variant listed in the variants
            file.

    """
    with open(file_path, 'r') as variant_file:
        variant_data = variant_file.readlines()

    variants = []
    for line in variant_data:
        if line.startswith('VARIANTS :='):
            variants.extend(line.split()[2:])

    variants = [variant + '.mk' for variant in variants]
    return variants


def makeVariant(workspace_path, variant_file_path, operations):
    """Configures and performs a make operation for the specified variant.

    Args:
        workspace_path (string): Path to the directory in which to run make.
        variant_file_path (string): Path to this build's variant file in order
            to configure build type.
        operations (dict): Dictionary containing build information for this
            variant.

    """
    sequence = list(operations.keys())
    sequence.sort()

    prev_config = None
    for step in sequence:
        make_config = operations[step].get('config')
        make_op = operations[step].get('operation')
        make_directories = operations[step].get('dirs')

        if make_config is not prev_config:
            prev_config = make_config
            updateBuildType(variant_file_path, make_config)

        for project_dir in make_directories:
            project_path = os.path.join(workspace_path, project_dir)
            doMakeOperation(project_path, make_op)
            print('\n***********************', project_dir,
                  'DONE *************************\n')


def updateBuildType(variant_file_path, build_type):
    """Updates the variant BUILD_TYPE if changed.

    Args:
        variant_file_path (string): path to the variant file
        build_type (string): build configuration type to set

    """

    config_updated = None
    regex_pattern = 'BUILD_TYPES := (.*)'
    variant_data = []

    readVariantFile(variant_file_path, variant_data)

    for i, line in enumerate(variant_data):
        match = re.match(regex_pattern, line)

        if match is not None:
            if match.group(1) is not build_type:
                variant_data[i] = 'BUILD_TYPES := ' + build_type + '\n'
                config_updated = True
            else:
                config_updated = False
                break

    if config_updated is None:
        variant_data.append('BUILD_TYPES := ' + build_type + '\n')
        config_updated = True

    if config_updated is True:
        writeVariantFile(variant_file_path, variant_data)


def readVariantFile(variant_file_path, variant_data):
    """Reads variant file into the supplied list.

    Args:
        variant_file_path (string): Path to the variant file.
        variant_data (list): List to store the lines of the variant file.

    """
    with open(variant_file_path, 'r') as variant_file:
        variant_data[:] = variant_file.readlines()


def writeVariantFile(variant_file_path, variant_data):
    with open(variant_file_path, mode='w') as variant_file:
        variant_file.writelines(variant_data)


def doMakeOperation(project_dir_path, operation=''):
    """Performs make operation and generates log files.

    Args:
        project_dir_path (type): Description of parameter `project_dir_path`.
        operation (type): Make rule to execute. Defaults to ''.

    """
    command = ['make']
    if operation is not '' and operation is not None:
        command.append(operation)
    pattern = r".*\\(.+)\\*"
    match = re.match(pattern, project_dir_path)
    log_name = datetime.now().strftime('log_' + match.group(1)
                                       + '_%H_%M_%d_%m_%Y.log')
    log_path = os.path.join(DEFAULT_LOG_FILE_PATH, log_name)
    build_comment = project_dir_path + ' make ' + operation
    print(build_comment)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'w+') as log_file:
        log_file.write(build_comment + '\n\n')
        proc = sp.run(command, cwd=project_dir_path,
                      stdout=log_file, stderr=sp.PIPE, encoding='utf-8')
        if proc.returncode is not 0:
            print(match.group(1), ':', 'make', operation, ': make error',
                  proc.returncode, ': check logs for details')
            print(proc.stderr)
            error_stream = proc.stderr
            print(match.group(1), ':', error_stream)
            error_log_path = log_path[:-4]+'_error.log'
            with open(error_log_path, 'w+') as error_log:
                error_log.write(error_stream)
                print(match.group(1), ': Error log created :', error_log_path)


if __name__ == '__main__':
    main()
