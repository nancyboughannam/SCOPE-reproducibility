function output = RUN_MATLAB(source, dataRoot)
% RUN_MATLAB                 Replot the archived paper data (no simulation).
% RUN_MATLAB('rerun')        Plot a completed full run in reruns/paper.
% RUN_MATLAB('rerun', path)  Plot a completed full run at a custom path.
root = fileparts(mfilename('fullpath'));
if nargin < 1, source = 'archived'; end
assert(any(strcmp(source,{'archived','rerun'})), 'Source must be archived or rerun.');
if nargin < 2
    if strcmp(source,'archived'), dataRoot=fullfile(root,'results');
    else, dataRoot=fullfile(root,'reruns','paper'); end
end
addpath(fullfile(root,'matlab'));
if strcmp(source,'archived')
    mainRoot=fullfile(dataRoot,'v5_guard_off');
else
    mainRoot=fullfile(dataRoot,'main');
end
deltaRoot=fullfile(dataRoot,'delta_t');
assert(isfile(fullfile(mainRoot,'completion.json')) && isfile(fullfile(deltaRoot,'completion.json')), ...
    'Both completed main and Delta T studies are required. See docs/REPRODUCIBILITY.md for individual plotting.');
output=fullfile(root,'outputs',['figures_' datestr(now,'yyyymmdd_HHMMSS_FFF')]);
assert(~isfolder(output),'Output exists; wait a moment and rerun.');
mkdir(output);
plot_scope_original_with_random(mainRoot,fullfile(output,'scope'));
plot_delta_t_results(deltaRoot,fullfile(output,'delta_t'));
info=struct('source',source,'data_root',dataRoot,'created',datestr(now,30));
fid=fopen(fullfile(output,'SOURCE.json'),'w');
assert(fid~=-1,'Cannot write figure provenance.');
cleanup=onCleanup(@() fclose(fid));
fprintf(fid,'%s\n',jsonencode(info));
fprintf('\nMATLAB FIGURES COMPLETE: %s\n',output);
fprintf('Return to Terminal and run: bash ZIP_RESULTS.sh %s\n',source);
end
