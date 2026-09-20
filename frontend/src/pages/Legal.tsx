import { useEffect } from "react";

/**
 * Static legal pages, rendered by a tiny hash router (#/privacy, #/terms).
 * No router dependency — the marketing surface is a single screen.
 *
 * The copy describes exactly what the code does (verified):
 * - CV data is sent once to generate the file, never persisted server-side.
 * - A draft autosaves to the user's own browser localStorage only.
 * - No accounts, no tracking, no analytics, no cookies.
 */

function useHashRoute(onNavigate: (route: string) => void) {
  useEffect(() => {
    const sync = () => onNavigate(window.location.hash.replace(/^#/, ""));
    sync();
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, [onNavigate]);
}

function LegalShell({
  title,
  updated,
  children,
}: {
  title: string;
  updated: string;
  children: React.ReactNode;
}) {
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);
  return (
    <div className="legal-page">
      <p>
        <a href="#/" className="legal-back">
          ← Back to the CV builder
        </a>
      </p>
      <h1>{title}</h1>
      <p className="legal-updated">Last updated: {updated}</p>
      <div className="legal-body">{children}</div>
    </div>
  );
}

function PrivacyPolicy() {
  return (
    <LegalShell title="Privacy Policy" updated="September 2026">
      <h2>The short version</h2>
      <p>
        No accounts, no database, no stored CVs, and no analytics. Your data
        is sent to our server only to build the document, processed in memory
        for the moment it takes to generate, and then discarded — never
        written to disk or any database.
      </p>

      <h2>What we collect</h2>
      <p>
        <strong>CV content you type:</strong> sent once per download to the
        document-generation endpoint, used only to build your file, and never
        written to disk or any database.
      </p>
      <p>
        <strong>Your draft copy:</strong> while you edit, a copy of your entries
        is saved in your own browser's local storage so an accidental refresh
        doesn't lose your work. This never leaves your device. Clear it any time
        with "Clear and restart", or by clearing your browser data.
      </p>
      <p>
        <strong>Server logs:</strong> our hosting provider may keep standard,
        short-lived technical logs (timestamps, response codes) for security and
        reliability. These logs are not used to build profiles and contain no CV
        content.
      </p>

      <h2>What we do NOT do</h2>
      <ul>
        <li>No accounts or sign-ups</li>
        <li>No cookies, no analytics, no advertising, no tracking pixels</li>
        <li>No selling or sharing of personal data — CV content is processed in memory only and never stored</li>
        <li>No third-party services receive your CV content; requests are processed by our API on its hosting provider over HTTPS</li>
      </ul>

      <h2>Where your data goes</h2>
      <p>
        The generation request travels over HTTPS from your browser to our API
        (hosted on a commercial cloud provider) and back. The document is built
        in the server's memory and streamed back to you as a download.
      </p>

      <h2>Your choices and rights</h2>
      <ul>
        <li>
          You don't need to give us any real personal data — use the tool with
          whatever you're comfortable typing.
        </li>
        <li>
          Because we don't store CV data, there is nothing for us to export or
          delete on request. Delete your browser draft with "Clear and restart".
        </li>
        <li>
          If you believe your data was collected through this site, contact us
          and we will investigate.
        </li>
      </ul>

      <h2>Children</h2>
      <p>
        The service is a general-purpose CV tool and is not directed at children
        under 13. We do not knowingly collect data from children.
      </p>

      <h2>Changes to this policy</h2>
      <p>
        If the product ever changes how it handles data — for example if we add
        optional accounts — this page will be updated before that change ships.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about this policy? Contact us at{" "}
        <a className="contact-email" href="mailto:hello@faysalmahmudprem.com">hello@faysalmahmudprem.com</a>.
      </p>
    </LegalShell>
  );
}

function TermsOfService() {
  return (
    <LegalShell title="Terms of Service" updated="September 2026">
      <h2>The short version</h2>
      <p>
        Use the tool freely, for real job hunting. Don't abuse it. The service
        is provided as-is, without warranty.
      </p>

      <h2>Acceptance</h2>
      <p>
        By using this website you agree to these terms. If you don't agree,
        please don't use the service.
      </p>

      <h2>The service</h2>
      <p>
        This is a free, browser-based CV builder. It converts the information
        you enter into a downloadable Word (<code>.docx</code>) document. No
        account is required, and nothing you enter is stored on our servers.
      </p>

      <h2>Acceptable use</h2>
      <ul>
        <li>
          Don't use the service to create fraudulent, misleading, or unlawful
          documents.
        </li>
        <li>
          Don't attempt to overload, disrupt, reverse-engineer for malicious
          purposes, or gain unauthorized access to the service.
        </li>
        <li>
          Automated abuse (scraping, spamming the generation endpoint) may be
          rate-limited or blocked.
        </li>
      </ul>

      <h2>Your content</h2>
      <p>
        You keep all rights to the content you enter. You grant us no license
        beyond the momentary technical processing needed to generate your
        document — and since nothing is stored, that license ends when your
        download completes.
      </p>

      <h2>No warranty</h2>
      <p>
        The service is provided "as is" and "as available" without warranties
        of any kind, express or implied, including merchantability, fitness for
        a particular purpose, and non-infringement. We don't guarantee that a
        generated CV will be accepted by any employer or applicant tracking
        system, or that the service will be uninterrupted or error-free.
      </p>

      <h2>Limitation of liability</h2>
      <p>
        To the maximum extent permitted by law, we are not liable for any
        indirect, incidental, or consequential damages arising from your use of
        the service — including lost job opportunities, lost data (use "Start
        over" carefully; drafts live only in your browser), or missed
        applications.
      </p>

      <h2>Availability</h2>
      <p>
        The service may change, break, or be discontinued at any time. On free
        hosting, the API may "wake up" slowly after idle periods — the first
        download can take longer.
      </p>

      <h2>Changes to these terms</h2>
      <p>
        We may update these terms from time to time. Continued use of the
        service after changes are posted constitutes acceptance.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about these terms? Contact us at{" "}
        <a className="contact-email" href="mailto:hello@faysalmahmudprem.com">hello@faysalmahmudprem.com</a>.
      </p>
    </LegalShell>
  );
}

export default function Legal({ route }: { route: string }) {
  return route === "/terms" ? <TermsOfService /> : <PrivacyPolicy />;
}

export { useHashRoute };
