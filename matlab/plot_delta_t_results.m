function output = plot_delta_t_results(studyRoot, output)
% Plot the COMPLETE fixed-model interval study in the existing paper style.
% MATLAB R2020a+; Times New Roman; 11 x 11 cm panels; PNG/PDF/FIG exports.
% No results are generated, smoothed, filtered, or selected by this script.
base = fileparts(mfilename('fullpath'));
if nargin < 1 || isempty(studyRoot), studyRoot = fileparts(base); end
if nargin < 2 || isempty(output)
    output = fullfile(studyRoot,['figures_delta_t_' datestr(now,'yyyymmdd_HHMMSS')]);
end
assert(~isfolder(output),'Choose a new output folder; existing figures are preserved.');
plan = jsondecode(fileread(fullfile(studyRoot,'study.json')));
status = jsondecode(fileread(fullfile(studyRoot,'completion.json')));
assert(strcmp(plan.workflow,'scope_delta_t_fixed_model_v1') && strcmp(plan.profile,'full'), ...
    'This plot requires the full Delta T study, not a smoke test or another study.');
assert(status.complete && status.completed == 120 && status.expected == 120, ...
    'Finish all 120 registered scenarios before generating paper figures.');
assert(isequal(plan.iterations(:),(3601:3610)') && isequal(plan.intervals_seconds(:),[15;30;60;90]), ...
    'Unexpected seeds or interval grid.');
assert(plan.lambda_value == 0.01 && plan.r_max == 0.15 && ~plan.retraining, ...
    'Controller settings differ from the registered sensitivity study.');
assert(any(strcmpi(listfonts,'Times New Roman')), ...
    'Times New Roman is required to preserve the existing paper style.');
M = readtable(fullfile(studyRoot,'mean_metrics.csv'),'TextType','string');
R = readtable(fullfile(studyRoot,'study_metrics.csv'),'TextType','string');
C = readtable(fullfile(studyRoot,'paired_comparisons.csv'),'TextType','string');
assert(height(C)==18 && all(C.family_tests==18) && all(C.n==10), ...
    'Missing registered paired comparisons or Holm family.');
assert(all(M.n==10) && all(isfinite(M.mean)) && all(isfinite(M.lower)) && all(isfinite(M.upper)), ...
    'Each summary must include ten seeds and finite intervals.');
assert(all(M.lower<=M.mean) && all(M.mean<=M.upper),'Invalid confidence intervals.');
cases = ["steady_900","steady_1800","shift_1200"];
labels = {'900 vehicles: steady','1800 vehicles: steady','1200 vehicles: shift'};
colors = [0 0.4470 0.7410; 0.15 0.55 0.25; 0.8500 0.3250 0.0980];
markers = {'o','s','^'}; lines = {'-','--','-.'};
dt = [15 30 60 90];
metrics = ["failure_pct","service_seconds"];
ylabs = {'Failed tasks (%)','Service time (s)'};
names = {'DeltaT_FailedTasks','DeltaT_ServiceTime'};

% Check the plotted summaries against individual run values, including seeds.
for c=1:3
    for j=1:4
        Q=R(R.scenario==cases(c) & R.interval_seconds==dt(j) & R.application=="ALL_APPS",:);
        assert(height(Q)==10 && isequal(sort(Q.iteration),(3601:3610)'), ...
            'Missing or repeated seed in a plotted cell.');
        for k=1:2
            S=M(M.scenario==cases(c) & M.interval_seconds==dt(j) & ...
                M.application=="ALL_APPS" & M.metric==metrics(k),:);
            assert(height(S)==1,'Missing/duplicate plotted summary.');
            v=Q.(char(metrics(k))); m=mean(v); h=2.262157162854099*std(v)/sqrt(10);
            assert(max(abs([S.mean-m S.lower-(m-h) S.upper-(m+h)]))<1e-9, ...
                'Plot summary disagrees with raw per-run metrics.');
        end
    end
end
mkdir(output);
for k=1:2
    fig=figure('Visible','off','Color','w','Units','centimeters','Position',[6 3 11 11]);
    ax=axes('Parent',fig,'FontName','Times New Roman','FontSize',12,'Color','none');
    hold(ax,'on'); axis(ax,'square'); grid(ax,'off'); box(ax,'on');
    set(fig,'PaperUnits','centimeters','PaperPositionMode','manual', ...
        'PaperPosition',[0 0 11 11],'PaperSize',[11 11]);
    for c=1:3
        V=zeros(4,3);
        for j=1:4
            S=M(M.scenario==cases(c) & M.interval_seconds==dt(j) & ...
                M.application=="ALL_APPS" & M.metric==metrics(k),:);
            V(j,:)=[S.mean S.mean-S.lower S.upper-S.mean];
        end
        errorbar(ax,dt,V(:,1),V(:,2),V(:,3),'Color',colors(c,:), ...
            'Marker',markers{c},'LineStyle',lines{c},'LineWidth',1.5, ...
            'MarkerSize',6,'DisplayName',labels{c});
    end
    set(ax,'XTick',dt); xlim(ax,[12 93]);
    xlabel(ax,'Planning interval, \Delta T (s)','FontSize',13,'Interpreter','tex');
    ylabel(ax,ylabs{k},'FontSize',13);
    legend(ax,'show','Location','best','FontName','Times New Roman', ...
        'FontSize',10,'Interpreter','none','Box','off');
    % Use complete recorded intervals; do not clip negative statistical bounds.
    drawnow;
    exportgraphics(ax,fullfile(output,[names{k} '.pdf']),'ContentType','vector');
    exportgraphics(ax,fullfile(output,[names{k} '.png']),'Resolution',300);
    savefig(fig,fullfile(output,[names{k} '.fig']));
    close(fig);
end
copyfile(fullfile(studyRoot,'mean_metrics.csv'),fullfile(output,'all_mean_metrics.csv'));
copyfile(fullfile(studyRoot,'paired_comparisons.csv'),fullfile(output,'paired_comparisons.csv'));
copyfile(fullfile(base,'figure_delta_t.tex'),fullfile(output,'figure_delta_t.tex'));
fprintf('Delta T panels saved to: %s\n',output);
fprintf('120 scenarios; ten paired seeds; means and pointwise 95%% t intervals.\n');
fprintf('Use both panels together as ONE figure in the manuscript.\n');
fprintf('Frozen 60-second-trained models; native telemetry windows change with Delta T.\n');
fprintf('This is sensitivity of the deployed controller, not an interval-specific retraining study.\n');
fprintf('Failure denominator: completed + failed. Service time: completed tasks only.\n');
fprintf('Movement measures configuration distance, not physical migration overhead.\n');
end
