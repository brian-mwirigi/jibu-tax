import fs from 'fs';
import path from 'path';
import git from 'isomorphic-git';

const rootDir = path.resolve('..'); // c:\Users\RawBUTT\Desktop\jibu-tax

async function run() {
  console.log('Target directory:', rootDir);

  // 1. Init repo if needed
  if (!fs.existsSync(path.join(rootDir, '.git'))) {
    console.log('Initializing git repository...');
    await git.init({ fs, dir: rootDir, defaultBranch: 'main' });
  }

  // 2. Set config
  await git.setConfig({
    fs,
    dir: rootDir,
    path: 'user.name',
    value: 'Role 6 Telemetry Engineer',
  });
  await git.setConfig({
    fs,
    dir: rootDir,
    path: 'user.email',
    value: 'role6@jibutax.internal',
  });

  // 3. Add remote
  try {
    await git.addRemote({
      fs,
      dir: rootDir,
      remote: 'origin',
      url: 'https://github.com/brian-mwirigi/jibu-tax.git',
    });
    console.log('Remote origin added: https://github.com/brian-mwirigi/jibu-tax.git');
  } catch (e) {
    console.log('Remote note:', e.message);
  }

  // 4. Stage all tracked/untracked files
  const statusMatrix = await git.statusMatrix({ fs, dir: rootDir });
  console.log(`Found ${statusMatrix.length} files in status matrix.`);

  for (const [filepath, headStatus, workdirStatus, stageStatus] of statusMatrix) {
    if (filepath.startsWith('frontend/node_modules')) continue;
    if (filepath.startsWith('.venv')) continue;
    if (filepath.startsWith('.git')) continue;
    
    if (workdirStatus !== 0) {
      await git.add({ fs, dir: rootDir, filepath });
    }
  }
  console.log('Staged files.');

  // 5. Commit
  const sha = await git.commit({
    fs,
    dir: rootDir,
    message: 'feat(frontend): implement Role 6 real-time telemetry dashboard & direct backend integration',
    author: {
      name: 'Role 6 Telemetry Engineer',
      email: 'role6@jibutax.internal',
    },
  });
  console.log('Committed commit SHA:', sha);

  // 6. Create and checkout branch feat/role6-telemetry-dashboard
  await git.branch({
    fs,
    dir: rootDir,
    ref: 'feat/role6-telemetry-dashboard',
    checkout: true,
  });
  console.log('Checked out branch: feat/role6-telemetry-dashboard');

  const currentBranch = await git.currentBranch({ fs, dir: rootDir });
  console.log('Current branch is now:', currentBranch);
}

run().catch((err) => {
  console.error('Error during git ops:', err);
  process.exit(1);
});
