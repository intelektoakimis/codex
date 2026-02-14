import './globals.css';

export const metadata = {
  title: 'Will You Be My Valentine?',
  description: 'A cute and romantic valentine invitation'
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
