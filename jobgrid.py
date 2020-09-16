#!/usr/bin/env python
import PySimpleGUI as sg
import sys
import os
import csv
import pandas as pd
import re
# TODOS:
# Add props at run time


# sg.theme('Dark Red')
sg.theme('Dark Blue 3')
# print = sg.Print

bigfont = ("Arial", 16)
rule = ("Arial", 10)


def pad(s, l=12):
    return s.ljust(l, " ")

def getlines(filename):
    with open(filename, "r") as f:
        return [s.strip() for s in f.readlines()]


def choose_main():
    layout = [[sg.Text('Params file')],
              [sg.Input(key='-FILE-', visible=False, enable_events=True), sg.FileBrowse()]]
    event, values = sg.Window('File Compare', layout).read(close=True)
    mainwin(values['-FILE-'])
    # print(f'You chose: {values["-FILE-"]}')


def generate_scripts(values):
    grid = {}
    template = None
    experiments = None
    output_dir = None
    r = re.compile(r'\[([^\]]*)\]')

    for k, v in values.items():
        if "-PROP-" in str(k):
            k = k[6:]
            if values['-CHECK-' + k]:
                try:
                    min_, max_, step = [int(x) for x in [values[a + k] for a in ['-MIN-', '-MAX-', '-STEP-']]]
                    max_ = max_ + 1
                except:
                    raise ValueError("Invalid values for min/max/step")
                grid[k] = range(min_, max_, step)
            else:
                match = re.search(r, v)
                if match:
                    if not os.path.exists(match.group(1)):
                        raise ValueError(f"File {match.group(1)} specified as value not found.")
                    grid[k] = getlines(match.group(1))
                else:
                    grid[k] = v.split(",")
        elif k == "-OUTPUT-":
            output_dir = v
        elif k == "-TEMPLATE-":
            template = v
        elif k == "-EXPERIMENT-":
            experiments = v

    keys = list(grid.keys())
    results = _iterate([], keys, grid, {})

    if not os.path.exists(template):
        raise ValueError(f"File {template} not found.")

    exp_idx = 1
    if not os.path.exists(experiments):
        create = sg.popup_ok_cancel('Experiments file not found. Create new?')
        if create != "OK":
            raise ValueError(f"Experiments file {experiments} not found.")
        else:
            exp_df = pd.DataFrame(columns=["id"]).set_index("id")
            exp_idx = len(exp_df)
    else:
        try:
            exp_df = pd.read_csv(experiments, index_col="id")
            exp_idx += len(exp_df)
        except:
            raise ValueError("Invalid experiments file {experiments}")

    try:
        with open(template, "r") as f:
            template_lines = f.readlines()
    except:
        raise ValueError("Error reading template file.")

    if not os.path.exists(output_dir) and os.path.isdir(output_dir):
        raise ValueError(f"Output dir {output_dir} not valid.")

    sim_jobs = 9e9
    if values['-LIMIT-']:
        sim_jobs = int(values['-JOBS_SLIDER-'])

    firstjobs = []
    mem = int(values['-MEM-'])
    hours = int(values['-TIME-'])

    for idx in range(len(results)):
        script_id = str(exp_idx + idx).rjust(5, "0")
        next_job_id = None
        if len(firstjobs) < sim_jobs:
            firstjobs.append(f"sbatch {script_id}_batch.sh")

        if idx + sim_jobs < len(results):
            next_job_id = str(exp_idx + idx + sim_jobs).rjust(5, "0")

        prop_string = " ".join([f"--{k} {v}" for k, v in results[idx].items()])
        prop_string = prop_string.replace("{jobid}", script_id)
        for k, v in results[idx].items():
            exp_df.loc[exp_idx + idx, k] = v

        with open(f"{output_dir}/{script_id}_job.sh", "w") as f:
            for line in template_lines:
                if "SBATCH --mem=" in line:
                    line = f"#SBATCH --mem={mem}G\n"
                if "SBATCH --time" in line:
                    line = f"#SBATCH --time={hours}:00:00\n"
                if "{jobid}" in line:
                    line = line.replace("{jobid}", script_id)
                if "{props}" in line:
                    line = line.replace("{props}", prop_string)
                for k, v in results[idx].items():
                    line = line.replace("{" + k + "}", str(v))
                f.write(line)
            if next_job_id is not None:
                f.write(f"\nsbatch {next_job_id}_job.sh\n")
    exp_df.to_csv(experiments)
    sg.Print("\n".join(firstjobs))

def _iterate(results, keys, grid, props):
    k = keys[0]
    if len(keys) > 1:
        for x in range(len(grid[k])):
            p = props.copy()
            p[k] = grid[k][x]
            _iterate(results, keys[1:], grid, p)
    else:
        for x in range(len(grid[keys[0]])):
            props[k] = grid[k][x]
            results.append(props.copy())

    return results


def mainwin(pfile):
    # def mainwin(pfile):
    layout = []
    with open(pfile, "r") as f:
        lines = f.readlines()
    if "arg,values" in lines[0]:
        lines = lines[1:]
    lines = [x for x in lines if x[0] != "#"]
    options = {}
    fields = []

    ## Setup
    layout.append([sg.Text("OzSTAR GRID MAKER", size=(50, 1), justification="center", font=bigfont)])
    layout.append([sg.Text("JOB", font=bigfont)])
    layout.append([
        sg.Text("Mem:"), sg.InputText("12", key="-MEM-", size=(5, 1)),
        sg.Text("GB"),
        sg.Text("Time:"), sg.InputText("16", key="-TIME-", size=(5, 1)),
        sg.Text("Hours"),
    ])
    layout.append([
        sg.CBox("", default=False, key="-LIMIT-"),
        sg.Text("Limit to concurrent jobs:"),
        sg.Slider(range=(0, 30), key='-JOBS_SLIDER-', default_value=5, orientation="h")
    ])

    layout.append([sg.Text("", font=rule)])
    layout.append([sg.Text("GRID", font=bigfont)])
    checkbox = []
    for toks in csv.reader(lines, quotechar='"', delimiter=',',
                           quoting=csv.QUOTE_ALL, skipinitialspace=True):
        f = toks[0]
        fields.append(f)
        props = {}
        options[f] = props
        props['default'] = toks[1]
        props['min'] = toks[2]
        props['max'] = toks[3]
        props['step'] = toks[4]
        checkbox.append(toks[1]=="" and toks[2] != "" and toks[3] != "" and toks[4] != "")

    layout.append([
        sg.Text("Property", size=(18, 1)),
        sg.Text("Values", size=(16, 1)),
        sg.Text("grid", size=(4, 1)),
        sg.Text("min", size=(3, 1)),
        sg.Text("max", size=(4, 1)),
        sg.Text("step", size=(4, 1)),
    ]
    )
    for n, prop in enumerate(fields):
        layout.append(
            [
                sg.Text(f"{pad(prop)}:"),
                sg.InputText(f"{options[prop]['default']}", size=(22, 1), key=f"-PROP-{prop}"),
                sg.CBox('', default=checkbox[n], key=f"-CHECK-{prop}"),
                sg.InputText(options[prop]['min'], size=(4, 1), key=f"-MIN-{prop}"),
                sg.InputText(options[prop]['max'], size=(4, 1), key=f"-MAX-{prop}"),
                sg.InputText(options[prop]['step'], size=(4, 1), key=f"-STEP-{prop}"),
            ]
        )

    layout.append([sg.Text("", font=rule)])

    layout.append([sg.Text("TEMPLATE", font=bigfont)])
    layout.append([
        sg.Text('Template', size=(12, 1)), sg.Input("template.sh", key="-TEMPLATE-"),
        sg.FileBrowse(button_text="Select"),
    ])
    layout.append([
        sg.Text('Output dir', size=(12, 1)), sg.Input(".", key="-OUTPUT-"),
        sg.FolderBrowse(button_text="Select", initial_folder=".", ),
    ])
    layout.append([
        sg.Text('Record file', size=(12, 1)), sg.Input("experiments.csv", key="-EXPERIMENT-"),
        sg.FolderBrowse(button_text="Select", initial_folder=".", ),
    ])

    statusbar = sg.StatusBar("            ", key="-STATUS-")
    layout.append([sg.Button("Generate"), sg.Button("Quit")])
    layout.append([statusbar])

    window = sg.Window('SLURM Gridder', layout)

    while True:
        if window.was_closed():
            break
        event, values = window.read(close=False)
        if event == "Quit":
            break
        try:
            generate_scripts(values)
        except ValueError as e:
            sg.popup('Error:', str(e))
        window['-STATUS-'].update("Success.")

    window.close()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        choose_main()
    else:
        mainwin(sys.argv[1])
