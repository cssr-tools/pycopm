# SPDX-FileCopyrightText: 2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Download the Smeaheia data set. Update your affiliation and
country accordingly."""

from pathlib import Path
from zipfile import ZipFile

from playwright.sync_api import sync_playwright

RESOURCE_URL = (
    "https://co2datashare.org/dataset/smeaheia-dataset/"
    "resource/6458d49e-ae92-47fa-8da4-ca1192ef28cf"
)

outdir = Path("test_outputs/smeaheia")
outdir.mkdir(parents=True, exist_ok=True)

zipfile = outdir / "simulation_models.zip"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    page.goto(RESOURCE_URL)
    page.check('input[name="license_accepted"]')
    page.click("#direct_download")
    page.fill('input[name="affiliation"]', "NORCE Research AS")
    page.select_option('select[name="country"]', "Norway")

    with page.expect_download() as download_info:
        page.click('button[name="download"]')

    download = download_info.value
    download.save_as(str(zipfile))

    browser.close()

with ZipFile(zipfile, "r") as zf:
    zf.extractall(outdir)
zipfile.unlink()
