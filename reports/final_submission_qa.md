# Final submission verification

## Manuscript

- Built the seven-page IEEEtran PDF with Tectonic and BibTeX. Kept the class margins and numbered citations. Reordered the double-column float declarations and added a bibliography barrier. Balanced the final reference columns using the IEEEtran reference trigger.
- Checked the rendered pages at 135 dpi. Figures 1–7 and Tables I–II precede References. Figure 2 is the proposed framework on page 3. Figure 7 is on page 6. References is the final section on page 7 and contains 18 sequential entries.
- The final TeX log contains no overfull boxes, missing characters, missing graphics, unresolved citations or unresolved references. TeX emitted underfull float-spacing diagnostics. The rendered pages were checked for gaps and overlaps.
- Checked manuscript source, PDF text and metadata for repository details, local paths, personal contacts and machine specifications. The authors, university affiliation and supervisor acknowledgment are present.

## Numerical integrity

- Verified the archived results, predictors, split inputs, frozen configuration, figures and numerical macros by SHA-256 against the pre-finalization snapshot. Regenerated the manuscript macros in a temporary copy and confirmed a byte-for-byte match. The article text and captions also match the previous source when the layout instructions and float relocation are excluded.
- Seven automated checks passed, including recomputation of metrics from held-out predictions, the archived comparison verdict, source timing, split validation, and manuscript inputs. The preprocessing unit test uses synthetic values.

## Handoff

- The full archive includes code, dependencies, tests, citation metadata, dataset provenance, permitted derived data, analysis outputs, seven figure sets, editable paper files and the final PDF.
- The Overleaf ZIP places the main document, numerical macros and bibliography at its root. It includes all seven vector figure dependencies and uses standard TeX packages. The extracted source built in a fresh local directory and reproduced the final page layout.
- The official-download script retrieved both workbooks into the extracted package and verified 162 and 187 observations, including MD5 and SHA-256.
- The published release delivers the PDF and both ZIPs. Raw workbooks and raster caches are retrieved through the documented official source workflow.
