import { lazy, type ComponentType } from 'react'
import type { IconName } from './icons'

const CommandCenter = lazy(() =>
  import('@/features/overview/OverviewPage').then((module) => ({
    default: module.OverviewPage,
  })),
)

const SiteTwin = lazy(() =>
  import('@/features/site/SiteScenePage').then((module) => ({
    default: module.SiteScenePage,
  })),
)

const Electrical = lazy(() =>
  import('@/features/electrical/ElectricalTopologyPage').then((module) => ({
    default: module.ElectricalTopologyPage,
  })),
)

const Grid = lazy(() =>
  import('@/features/electrical/GridConnectionPage').then((module) => ({
    default: module.GridConnectionPage,
  })),
)

const Fleet = lazy(() =>
  import('@/features/charging/ChargerFleetPage').then((module) => ({
    default: module.ChargerFleetPage,
  })),
)

const Inspection = lazy(() =>
  import('@/features/charging/ChargerDetailsPage').then((module) => ({
    default: module.ChargerDetailsPage,
  })),
)

const Solar = lazy(() =>
  import('@/features/generation/SolarProductionPage').then((module) => ({
    default: module.SolarProductionPage,
  })),
)

const BatteryScreen = lazy(() =>
  import('@/features/storage/BatteryStatePage').then((module) => ({
    default: module.BatteryStatePage,
  })),
)

const Alarms = lazy(() =>
  import('@/features/alarms/AlarmTriagePage').then((module) => ({
    default: module.AlarmTriagePage,
  })),
)

const Telemetry = lazy(() =>
  import('@/features/telemetry/TelemetryPipelinePage').then((module) => ({
    default: module.TelemetryPipelinePage,
  })),
)

const KpiValidation = lazy(() =>
  import('@/features/telemetry/MeasurementValidationPage').then((module) => ({
    default: module.MeasurementValidationPage,
  })),
)

const Health = lazy(() =>
  import('@/features/system/SystemHealthPage').then((module) => ({
    default: module.SystemHealthPage,
  })),
)

const GraphView = lazy(() =>
  import('@/features/topology/AssetGraphPage').then((module) => ({
    default: module.AssetGraphPage,
  })),
)

const Forecasts = lazy(() =>
  import('@/features/forecasting/ForecastsPage').then((module) => ({
    default: module.ForecastsPage,
  })),
)

const Dispatch = lazy(() =>
  import('@/features/optimization/DispatchOptimizerPage').then((module) => ({
    default: module.DispatchOptimizerPage,
  })),
)

const ScenarioBuilder = lazy(() =>
  import('@/features/scenarios/ScenarioBuilderPage').then((module) => ({
    default: module.ScenarioBuilderPage,
  })),
)

const Comparison = lazy(() =>
  import('@/features/scenarios/ScenarioComparisonPage').then((module) => ({
    default: module.ScenarioComparisonPage,
  })),
)

const DemoStream = lazy(() =>
  import('@/features/streaming/TelemetryStreamPage').then((module) => ({
    default: module.TelemetryStreamPage,
  })),
)

const RlLab = lazy(() =>
  import('@/features/reinforcement-learning/PolicyEvaluationPage').then((module) => ({
    default: module.PolicyEvaluationPage,
  })),
)

type Screen = {
  path: string
  title: string
  group: string
  icon: IconName
  component: ComponentType
}

export const screens: Screen[] = [
  {
    path: '/',
    title: 'Command Center',
    group: 'Operations',
    icon: 'overview',
    component: CommandCenter,
  },
  {
    path: '/site',
    title: '3D Site Twin',
    group: 'Operations',
    icon: 'solar',
    component: SiteTwin,
  },
  {
    path: '/electrical',
    title: 'Electrical One-Line',
    group: 'Operations',
    icon: 'electricity',
    component: Electrical,
  },
  {
    path: '/chargers',
    title: 'Charger Fleet & Queue',
    group: 'Operations',
    icon: 'charging',
    component: Fleet,
  },
  {
    path: '/inspect',
    title: 'Charger Inspection',
    group: 'Operations',
    icon: 'inspection',
    component: Inspection,
  },
  {
    path: '/solar',
    title: 'Solar Production',
    group: 'Operations',
    icon: 'sun',
    component: Solar,
  },
  {
    path: '/battery',
    title: 'Battery State',
    group: 'Operations',
    icon: 'battery',
    component: BatteryScreen,
  },
  {
    path: '/grid',
    title: 'Grid & Transformer',
    group: 'Operations',
    icon: 'electricity',
    component: Grid,
  },
  {
    path: '/alarms',
    title: 'Alarm Triage',
    group: 'Investigate',
    icon: 'alarm',
    component: Alarms,
  },
  {
    path: '/telemetry',
    title: 'Telemetry Pipeline',
    group: 'Investigate',
    icon: 'telemetry',
    component: Telemetry,
  },
  {
    path: '/stream',
    title: 'Simulated MQTT Stream',
    group: 'Investigate',
    icon: 'forecast',
    component: DemoStream,
  },
  {
    path: '/graph',
    title: 'Ontology & Graph',
    group: 'Investigate',
    icon: 'graph',
    component: GraphView,
  },
  {
    path: '/forecasts',
    title: 'Forecasts',
    group: 'Plan',
    icon: 'forecast',
    component: Forecasts,
  },
  {
    path: '/dispatch',
    title: 'Dispatch Optimizer',
    group: 'Plan',
    icon: 'optimizer',
    component: Dispatch,
  },
  {
    path: '/scenarios',
    title: 'Scenario Builder',
    group: 'Plan',
    icon: 'scenario',
    component: ScenarioBuilder,
  },
  {
    path: '/compare',
    title: 'Scenario Comparison',
    group: 'Plan',
    icon: 'compare',
    component: Comparison,
  },
  {
    path: '/rl-lab',
    title: 'PowerWise RL Lab',
    group: 'Plan',
    icon: 'optimizer',
    component: RlLab,
  },
  {
    path: '/validation',
    title: 'KPI Validation',
    group: 'Assurance',
    icon: 'validation',
    component: KpiValidation,
  },
  {
    path: '/health',
    title: 'Architecture & Health',
    group: 'Assurance',
    icon: 'architecture',
    component: Health,
  },
]
