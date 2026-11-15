import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './query-client'
import { Workbench } from './Workbench'

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Workbench />
    </QueryClientProvider>
  )
}
