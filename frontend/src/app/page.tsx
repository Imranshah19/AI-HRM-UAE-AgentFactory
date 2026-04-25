import { redirect } from 'next/navigation';

// Root "/" → redirect to dashboard (middleware will redirect to /login if unauthenticated)
export default function RootPage() {
  redirect('/dashboard');
}
