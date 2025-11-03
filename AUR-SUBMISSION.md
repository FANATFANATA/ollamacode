# Submitting OllamaCode to the Arch User Repository (AUR)

This guide will help you submit OllamaCode to the AUR so users can install it with `yay`, `paru`, or other AUR helpers.

## Prerequisites

1. **GitHub account** (already have: r3dg0d)
2. **SSH key set up** for AUR access
3. **AUR account** - Create one at https://aur.archlinux.org/register

## Step 1: Set Up SSH Key for AUR

The AUR requires SSH authentication. You'll need to add your SSH public key to your AUR account.

1. **Generate SSH key (if you don't have one):**
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

2. **Add your SSH key to AUR:**
   - Go to https://aur.archlinux.org/account/
   - Click "Add SSH Key"
   - Paste the contents of `~/.ssh/id_ed25519.pub` (or your public key file)

## Step 2: Clone the AUR Repository

```bash
# Navigate to a temporary directory
cd /tmp

# Clone the AUR repository (use your AUR username)
git clone ssh://aur@aur.archlinux.org/ollamacode.git
cd ollamacode
```

## Step 3: Copy PKGBUILD and .SRCINFO

```bash
# Copy the PKGBUILD from your project
cp ~/Documents/ollamacode/PKGBUILD .
cp ~/Documents/ollamacode/.SRCINFO .
```

## Step 4: Update .SRCINFO

The `.SRCINFO` file needs to be regenerated. However, since we're using git source, you may need to adjust it:

```bash
# Verify the PKGBUILD is correct
cd /tmp/ollamacode
cat PKGBUILD
```

## Step 5: Test the Package Build

Before submitting, test that the package builds correctly:

```bash
# Install base-devel if not already installed
sudo pacman -S base-devel

# Build the package
makepkg -s

# Check for errors
```

## Step 6: Generate .SRCINFO

The `.SRCINFO` file should be generated from the PKGBUILD:

```bash
# Make sure you have the latest version of makepkg
makepkg --printsrcinfo > .SRCINFO
```

## Step 7: Commit and Push to AUR

```bash
# Configure git (if not already)
git config user.name "r3dg0d"
git config user.email "r3dg0d@users.noreply.github.com"

# Add files
git add PKGBUILD .SRCINFO

# Commit
git commit -m "Initial commit: Add ollamacode package"

# Push to AUR
git push origin master
```

## Step 8: Verify Submission

1. Visit https://aur.archlinux.org/packages/ollamacode
2. Verify the package appears correctly
3. Check that all fields are filled in properly

## Updating the Package

When you make updates to OllamaCode:

1. **Update the version in PKGBUILD:**
   ```bash
   # Edit PKGBUILD and increment pkgver
   # pkgver=1.0.0 -> pkgver=1.0.1
   ```

2. **Update .SRCINFO:**
   ```bash
   makepkg --printsrcinfo > .SRCINFO
   ```

3. **Commit and push:**
   ```bash
   git add PKGBUILD .SRCINFO
   git commit -m "Update to version 1.0.1"
   git push
   ```

## Important Notes

- **Don't commit the `venv/` directory** - It's in .gitignore
- **Always test builds locally** before pushing to AUR
- **Follow AUR submission guidelines**: https://wiki.archlinux.org/title/AUR_submission_guidelines
- **Package naming**: The package name should match the git repository name
- **Maintainer field**: Update the maintainer email in PKGBUILD if needed

## Troubleshooting

### SSH Connection Issues

If you get SSH connection errors:
```bash
# Test SSH connection
ssh -T aur@aur.archlinux.org

# Should output: "Logged in as r3dg0d"
```

### Build Errors

If `makepkg` fails:
- Check that all dependencies are installed
- Verify the PKGBUILD syntax
- Check for typos in file paths

### .SRCINFO Generation

If `.SRCINFO` doesn't generate correctly:
```bash
# Make sure you're using a recent version of pacman
sudo pacman -Syu pacman

# Regenerate
makepkg --printsrcinfo > .SRCINFO
```

## AUR Package Maintenance

Once your package is in the AUR, users can install it with:

```bash
# Using yay
yay -S ollamacode

# Using paru
paru -S ollamacode

# Manual installation
git clone https://aur.archlinux.org/ollamacode.git
cd ollamacode
makepkg -si
```

You'll need to maintain the package:
- Keep it updated with new releases
- Respond to user comments and requests
- Fix any reported issues

For more information, see: https://wiki.archlinux.org/title/Arch_User_Repository

