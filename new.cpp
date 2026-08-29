#include <bits/stdc++.h>
using namespace std;

using ll = long long;

const int MOD = 998244353;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    cin >> t;

    while (t--) {
        int n, m, d;
        cin >> n >> m >> d;

        vector<string> grid(n);

        for (auto &row : grid) {
            cin >> row;
        }

        vector<ll> prev(m, 0), enter(m, 0);
        vector<ll> cur(m, 0), pre(m + 1, 0);

        int D = (int)sqrt(1LL * d * d - 1);

        for (int r = n - 1; r >= 0; r--) {

            fill(enter.begin(), enter.end(), 0);

            if (r == n - 1) {

                for (int j = 0; j < m; j++) {
                    if (grid[r][j] == 'X') {
                        enter[j] = 1;
                    }
                }
            }
            else {

                pre[0] = 0;

                for (int j = 0; j < m; j++) {
                    pre[j + 1] =
                        (pre[j] + prev[j]) % MOD;
                }

                for (int j = 0; j < m; j++) {

                    if (grid[r][j] == 'X') {

                        int l = max(0, j - D);
                        int rr = min(m - 1, j + D);

                        enter[j] =
                            (pre[rr + 1] - pre[l] + MOD) % MOD;
                    }
                }
            }

            pre[0] = 0;
            for (int j = 0; j < m; j++) {
                pre[j + 1] =
                    (pre[j] + enter[j]) % MOD;
            }
            fill(cur.begin(), cur.end(), 0);
            for (int j = 0; j < m; j++) {

                if (grid[r][j] == '#')
                    continue;

                int L = max(0, j - d);
                int R = min(m - 1, j + d);

                cur[j] =
                    (pre[R + 1] - pre[L] + MOD) % MOD;
            }

            prev = cur;
        }

        ll ans = 0;

        for (int j = 0; j < m; j++) {
            ans = (ans + prev[j]) % MOD;
        }

        cout << ans << '\n';
    }

    return 0;
}
