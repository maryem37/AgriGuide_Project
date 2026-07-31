"""
Phase B — fine-tune BreizhCrops' pretrained TempCNN.

Uses the dataset's NATIVE 9-class classmapping.csv as-is (no remap
needed — the pretrained checkpoint was itself trained on exactly these
9 classes, so we're fine-tuning into the same label space, not a new
one). Output of this script is a checkpoint that
`app/services/dl_service.py` loads for inference.

Why fine-tune instead of train from scratch: the pretrained TempCNN
already learned general Sentinel-2 temporal patterns for these crop
types; a few epochs at a low learning rate adapts it rather than
re-learning from zero, which is the difference between "runs in an
afternoon on Colab free tier" and "needs real training infrastructure
we don't have."

Ported as-is from the standalone `agri-advisor-parcelle` prototype. Run
on Colab (recommended — free GPU) or locally with a CUDA GPU if you
have one; CPU works too, just slower:

    pip install breizhcrops
    python -m scripts.finetune_dl_service --datapath ./breizhcrops_dataset --epochs 8

First run downloads real Sentinel-2+RPG data from BreizhCrops' S3
bucket (a few GB depending on level/region).
"""
import argparse
import os

import torch
import pandas as pd
import sklearn.metrics
from torch.optim import Adam
from torch.utils.data import DataLoader, ConcatDataset
from tqdm import tqdm

import breizhcrops
from breizhcrops.models.pretrained import pretrained as load_pretrained


def get_dataloaders(datapath: str, level: str, batchsize: int, workers: int):
    """Train on frh01+frh02+frh03, validate on frh04 — same held-out-region
    split BreizhCrops' own paper uses, so your reported numbers are
    comparable to their published baselines."""
    regions = {
        r: breizhcrops.BreizhCrops(region=r, root=datapath, level=level)
        for r in ["frh01", "frh02", "frh03", "frh04"]
    }
    train_ds = ConcatDataset([regions["frh01"], regions["frh02"], regions["frh03"]])
    val_ds = regions["frh04"]

    train_loader = DataLoader(train_ds, batch_size=batchsize, shuffle=True, num_workers=workers)
    val_loader = DataLoader(val_ds, batch_size=batchsize, shuffle=False, num_workers=workers)
    return train_loader, val_loader, regions["frh01"].classname


def metrics(y_true, y_pred):
    return dict(
        accuracy=sklearn.metrics.accuracy_score(y_true, y_pred),
        kappa=sklearn.metrics.cohen_kappa_score(y_true, y_pred),
        f1_macro=sklearn.metrics.f1_score(y_true, y_pred, average="macro", zero_division=0),
        f1_weighted=sklearn.metrics.f1_score(y_true, y_pred, average="weighted", zero_division=0),
    )


def train_epoch(model, optimizer, criterion, loader, device):
    model.train()
    losses = []
    with tqdm(loader, desc="train", leave=False) as it:
        for x, y_true, _ in it:
            optimizer.zero_grad()
            loss = criterion(model(x.to(device)), y_true.to(device))
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
            it.set_postfix(loss=f"{loss.item():.3f}")
    return sum(losses) / len(losses)


def eval_epoch(model, criterion, loader, device):
    model.eval()
    y_true_all, y_pred_all, losses = [], [], []
    with torch.no_grad():
        with tqdm(loader, desc="val", leave=False) as it:
            for x, y_true, _ in it:
                logits = model(x.to(device))
                loss = criterion(logits, y_true.to(device))
                losses.append(loss.item())
                y_true_all.append(y_true)
                y_pred_all.append(logits.argmax(-1).cpu())
    y_true_all = torch.cat(y_true_all)
    y_pred_all = torch.cat(y_pred_all)
    return sum(losses) / len(losses), y_true_all, y_pred_all


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datapath", default="./breizhcrops_dataset")
    ap.add_argument("--level", default="L1C", help="must be L1C — the pretrained checkpoint expects 13 bands")
    ap.add_argument("--epochs", type=int, default=8, help="fine-tuning only needs a handful of epochs, not 150")
    ap.add_argument("--batchsize", type=int, default=256)
    ap.add_argument("--workers", type=int, default=0,
                     help="0 by default: BreizhCrops' data transform is a local closure, not picklable, "
                          "which crashes on Windows (spawn-based multiprocessing) whenever workers>0. "
                          "Safe to raise this on Linux/Colab (fork-based), where it doesn't hit this issue.")
    ap.add_argument("--lr", type=float, default=1e-4, help="low LR: adapting a pretrained model, not training fresh")
    ap.add_argument("--weight-decay", type=float, default=1e-6)
    ap.add_argument("--device", default=None)
    ap.add_argument("--out", default="./dl_checkpoints/tempcnn_finetuned.pth")
    args = ap.parse_args()

    device = torch.device(args.device or ("cuda" if torch.cuda.is_available() else "cpu"))
    print(f"device: {device}")

    if args.level != "L1C":
        print("WARNING: pretrained() checkpoints were trained on L1C (13 bands). "
              "L2A has only 10 selected bands — the pretrained weights won't load "
              "cleanly. Use --level L1C unless you're training a fresh model.")

    train_loader, val_loader, classnames = get_dataloaders(
        args.datapath, args.level, args.batchsize, args.workers
    )
    print(f"classes ({len(classnames)}): {list(classnames)}")

    model = load_pretrained("tempcnn", device=device)  # 13-dim input, 9 classes, seqlen 45 — matches our loader defaults exactly, no architecture surgery needed
    optimizer = Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    criterion = torch.nn.CrossEntropyLoss(reduction="mean")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    log = []
    best_f1_macro = -1.0

    for epoch in range(args.epochs):
        train_loss = train_epoch(model, optimizer, criterion, train_loader, device)
        val_loss, y_true, y_pred = eval_epoch(model, criterion, val_loader, device)
        scores = metrics(y_true, y_pred)
        print(
            f"epoch {epoch}: train_loss={train_loss:.3f} val_loss={val_loss:.3f} "
            + " ".join(f"{k}={v:.3f}" for k, v in scores.items())
        )
        scores.update(epoch=epoch, train_loss=train_loss, val_loss=val_loss)
        log.append(scores)

        if scores["f1_macro"] > best_f1_macro:
            best_f1_macro = scores["f1_macro"]
            torch.save({"model_state": model.state_dict(), "classnames": list(classnames)}, args.out)
            print(f"  -> new best (f1_macro={best_f1_macro:.3f}), saved to {args.out}")

    pd.DataFrame(log).set_index("epoch").to_csv(
        os.path.join(os.path.dirname(args.out), "finetune_log.csv")
    )
    print(f"\nDone. Best f1_macro={best_f1_macro:.3f}. Checkpoint: {args.out}")
    print(
        "\nNote on f1_macro vs f1_weighted: with 9 classes of very uneven "
        "real-world support (wheat/corn/rapeseed/barley/sunflower are common; "
        "orchards/nuts are rare in Brittany), f1_macro (unweighted average "
        "across classes) is the honest number for your report — f1_weighted "
        "will look better mostly because the common classes dominate it."
    )


if __name__ == "__main__":
    main()
