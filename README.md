# SLURM job gridder

## Overview

This is a simple GUI to create a suite of job scripts for a job scheduler. I made it for me to use on the OzSTAR supercomputer
and the SLURM job scheduler, as a way to learn [PySimpleGUI](https://pypi.org/project/PySimpleGUI/). It enables the user
to create many job scripts over an arbitrarily large grid (discrete values of many parameters).

The user specifies a list of parameters and optional default values. The GUI will allow the user to edit the values, 
either as an enumeration ("option a,option b,...") or a numerical range ([from] 1 [to] 10 [by] 2). The program will
iterate over all the possible combinations and create a job script.

The inputs to the program are:
- Parameters file: A CSV file with 5 columns per row (and an optional header row "arg,values,min,max,step"); only the arg 
name is mandatory.
- Template file: a template job scheduler script containing the string `{props}`
- An experiments file, where the parameters of a job and a job id will be stored as CSV; will be created the first time if not supplied.

Each job will be a copy of the template script file, except:
- Any occurrence of the string `{jobid}` will be replaced with a (generated) job id
- The string `{props}` will be replaced with the values from that grid point, formatted as per the following example:
`--arg1name argvalue1 --argname2 arg2value ...`
- `SBATCH --time` and `SBATCH --mem` will be replaced by directives with the specified values

In addition, if a maximum number of concurrent jobs is specified, then the program will "chain" scripts together so that 
when a job finishes it submits a new one to the queue. This is to avoid spamming the job queue with a large grid.

## Usage

### JOB
- *Mem*: The value of this parameter will be inserted into the appropriate part of the output scripts
- *Time*: As above
- *Concurrent Jobs*: The program will generate one script per grid point, but if a limit _n_ concurrent jobs is specified,
will include `sbatch` directives at the end of scripts such that only the first _n_ scripts should be directly submitted
to the queue by the user. The rest will occur as previous jobs finish.

### GRID
For each specified argument, the user specifies the list of possible parameters that make up the grid. This can be specified
in three ways:
- Directly as a comma-delimited enumeration: `optiona,optionb,optionc`
- Using a range for a numerical value: Select the 'grid' checkbox and specify a min, max and step. Note the max value is 
included in the grid, so (1, 9, 2) will generate the list [1, 3, 5, 7, 9].
- As a filename, using the format `[filename.txt]`. Each line in the specified file will be used as a grid value.

### TEMPLATE
- *Template*: The template script file as described above.
- *Output dir*: The location for the output scripts.
- *Experiments file*: A CSV file containing the parameter values for each grid point referenced by the jobid generated
by the program.
